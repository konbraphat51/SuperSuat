# BlockedOcr

ブロック型OCRパイプラインの入口。[Plan.md](Plan.md) の3段階を文書全体に対して実行し、
`OcrResult` のツリーを返す `Ocr` 実装。

English version: [BlockedOcr.md](BlockedOcr.md)

## 構成

```mermaid
classDiagram
    class Ocr {
        <<abstract>>
        +ocr(all_page_images: list[Image]) OcrResult*
    }
    class BlockedOcr {
        -blocker: Blocker
        -transcriber: Transcriber
        -organizer: Organizer
        -block_renderer: BlockRenderer
        +ocr(all_page_images: list[Image]) OcrResult
    }
    class Blocker {
        <<abstract>>
        +block(pages) BlockerResult
    }
    class Transcriber {
        <<abstract>>
        +transcribe(all_pages, blocker_result) TranscriptionResult
    }
    class BlockRenderer {
        +render(pages, blocker_result) list[Image]
    }
    class Organizer {
        +organize(all_page_images, all_page_images_rendered, blocker_result, transcription_result) OcrResult
    }
    Ocr <|-- BlockedOcr
    BlockedOcr o-- Blocker
    BlockedOcr o-- Transcriber
    BlockedOcr o-- Organizer
    BlockedOcr *-- BlockRenderer
```

各段階は構築済みのものを受け取る。どのモデルに処理させるかは呼び出し側の選択であり、
ローカルのレイアウトモデルとリモートのチャットモデルの組み合わせでも、より安価な
組み合わせでも同じパイプラインとして動く。`BlockRenderer` だけは例外でここで生成する。
モデルを持たず、選択の余地がないため。

## 実行の流れ

```mermaid
sequenceDiagram
    participant Caller
    participant BlockedOcr
    participant Blocker
    participant Transcriber
    participant BlockRenderer
    participant Organizer
    Caller->>BlockedOcr: ocr(all_page_images)
    BlockedOcr->>Blocker: block(all_page_images)
    Blocker-->>BlockedOcr: BlockerResult
    BlockedOcr->>Transcriber: transcribe(all_page_images, blocker_result)
    Transcriber-->>BlockedOcr: TranscriptionResult
    BlockedOcr->>BlockRenderer: render(all_page_images, blocker_result)
    BlockRenderer-->>BlockedOcr: ページごとの注釈付き画像
    BlockedOcr->>Organizer: organize(画像, 注釈付き画像, ブロック, 文字起こし)
    Organizer-->>BlockedOcr: OcrResult
    BlockedOcr-->>Caller: OcrResult
```

各段階は前段の出力を全て必要とするため、文書全体を単位として順に実行する。ページの
並列処理は `Blocker`・`Transcriber`・Organizerの `Classifier` の**内部**にあり、
このパイプラインの並列性はそこにある（[Blocker.ja.md](Blocker.ja.md) 参照）。

注釈付きページをOrganizerではなくここで描画するのは、これがOrganizerのモデルに
`block_id` とページ上のブロックの対応を示すためのものであり、文書全体分を一度描く方が
ページスキャンごとに描くより安く済むため。

## 規約

- ページ画像は一切変更しない。`BlockRenderer` はコピーに描画し、各段階は
  `all_page_images` を渡されたまま読むだけ。
- 変数に保持するページ番号は、OCRモジュール内の他の箇所と同様すべて0始まり。
