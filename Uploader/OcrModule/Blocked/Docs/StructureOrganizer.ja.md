# StructureOrganizer

ブロック分割OCRパイプラインの第3段階（[Plan.md](Plan.md) 参照）。`Blocker` が検出し
`Transcriber` が読み取ったブロックを、マルチモーダルモデルがページ単位で処理し、
ドキュメント構造を確定する。確定するのは、各テキストブロックの種別、各見出しの階層
レベル、各図のキャプション、そして読み順。

English version: [StructureOrganizer.md](StructureOrganizer.md)

## 構造

```mermaid
classDiagram
    class Organizer {
        -organizer_model: BaseChatModel
        +organize(all_page_images, all_page_images_rendered, blocker_result, transcription_result) OcrResult
        -_scan_page(page_index, all_page_images, page_image_rendered, processing_blocks)
    }
    class OrganizerAgent {
        -organizer_model: Runnable
        +scan_page(page_index, all_page_images, page_image_rendered, processing_blocks)
        -_request_orders(messages, page_index, batch_number) OrderBatch
        -_build_messages(page_index, all_page_images, page_image_rendered, processing_blocks) list[BaseMessage]
    }
    class OrderBatch {
        +orders: list[AnyOrder]
        +is_last_batch: bool
    }
    class Order {
        +order_label: ORDER_LABELS
    }
    class ProcessingBlock {
        +block_id: int
        +page_index: int
        +recognized_blocker_type: BlockType
        +new_type: str | None
        +have_been_labeled: bool
        +have_been_checked: bool
    }
    class ProcessingBlockText {
        +text: str
        +have_been_edited: bool
    }
    class ProcessingBlockTextHeading {
        +heading_level: int | None
    }
    class ProcessingBlockFigure {
        +bounding_box: tuple
        +have_caption_checked: bool
        +caption_text_block_id: int | None
    }
    class DataExporter {
        +export_processing_blocks_to_ocr_result(processing_blocks) OcrResult
    }
    Organizer ..> OrganizerAgent
    Organizer ..> DataExporter
    DataExporter ..> OcrResult
    OrganizerAgent ..> OrderBatch
    OrderBatch *-- Order
    Order <|-- OrderSetBlockType
    Order <|-- OrderSetHeadingLevel
    Order <|-- OrderReorder
    Order <|-- OrderDeleteBlock
    Order <|-- OrderEditBlock
    Order <|-- OrderSetCaption
    Order <|-- OrderMergeBlocks
    ProcessingBlock <|-- ProcessingBlockText
    ProcessingBlock <|-- ProcessingBlockFigure
    ProcessingBlockText <|-- ProcessingBlockTextHeading
    OrganizerAgent ..> ProcessingBlock
```

モデル自身はブロックを書き換えない。モデルは `OrderBatch` を返すだけで、
`ProcessingBlock` を変更するのは `execute_orders()` のみ。受け取ったJSONがどのorderかは
`order_label` で決まり、pydanticがこれをunionの判別子として使うため、各orderは自身の
スキーマで検証済みの状態で届く。

## ページスキャン

```mermaid
sequenceDiagram
    participant Organizer
    participant OrganizerAgent
    participant Model
    participant Executor as execute_orders
    Organizer->>OrganizerAgent: scan_page(page_index, all_page_images, page_image_rendered, processing_blocks)
    OrganizerAgent->>OrganizerAgent: _build_messages（プロンプト + ページ画像 + ブロック状態）
    loop is_last_batch まで、最大 MAX_BATCH_COUNT 回
        OrganizerAgent->>Model: invoke(messages)
        Model-->>OrganizerAgent: OrderBatch
        OrganizerAgent->>OrganizerAgent: deepcopy(processing_blocks)
        OrganizerAgent->>Executor: execute_orders(order_batch, copy)
        alt 適用できないorderがあった
            Executor-->>OrganizerAgent: ValueError / TypeError
            OrganizerAgent->>OrganizerAgent: 却下メッセージを追加、コピーは破棄
        else 適用できた
            Executor-->>OrganizerAgent: 編集済みのコピー
            OrganizerAgent->>OrganizerAgent: コピーを processing_blocks に書き戻す
            opt 最終バッチでない
                OrganizerAgent->>OrganizerAgent: 更新後のブロック状態を追加
            end
        end
    end
    OrganizerAgent-->>Organizer: processing_blocks をその場で編集
```

バッチはブロックのコピーに適用する。途中で失敗したバッチはブロックを一切変更せず、
その旨をモデルに伝えて再試行させる。ページの完了はモデルが `is_last_batch` で宣言し、
`MAX_BATCH_COUNT` は宣言しないモデルに対する保険でしかない。

ただし宣言すれば完了というわけではない。`_is_able_to_finish()` が、ページ上の全ブロックに
block_type があるか、見出しにレベルがあるか、図のキャプションが確認済みかを検査し、
足りなければ該当ブロックを名指しでモデルに差し戻す。通過したページのブロックには
`have_been_checked` が立つ。

## モデルに与えるコンテキスト

ページスキャンのたびにコンテキスト全体を送り直すため、そのページに必要なものだけに絞る。

- そのページが属している見出しのページ画像。外側から順に、直前ページ終了時点で開いて
  いた最も内側の見出し、その上の見出し、…、レベル1のドキュメントタイトルまで。長い
  ドキュメントでも見出しレベルを一貫させるのはこの仕組み。直前ページがH3で終わって
  いれば、そのH3・H2・H1のページ画像が渡る。同一ページに複数の上位見出しがある場合は、
  そのページ画像を1枚だけ送り、その中の見出しをまとめて示す。
- 直前 `RECENT_PAGE_COUNT` ページの画像。ページ境界をまたぐブロックのため。見出しの
  ページとして既に渡したページは重複して送らない。
- 現在のページ画像そのもの。
- 各ブロックの枠線と `block_id` を描画した現在のページ画像（`BlockRenderer` による。
  [Blocker.ja.md](Blocker.ja.md) 参照）。
- 現在のページと直前1ページの `ProcessingBlock` の状態を、現在の順序でJSON化したもの。
  ページ境界をまたぐブロックには1ページ分で足り、それ以前は確定済みなので含めない。

## Order一覧

| Order | 効果 |
| --- | --- |
| `set_block_type` | テキストブロックに `TEXT_BLOCK_TYPES` のいずれかを付与する。 |
| `set_heading_level` | 見出しにレベルを与え、同時に見出しとして分類する。 |
| `reorder` | ブロックを別のブロックの直前へ移動する。 |
| `delete_block` | ブロックを削除し、それを指していたキャプション参照も解除する。 |
| `edit_block` | 指定されたフィールドのみ変更する（種別・本文・見出しレベル）。 |
| `set_caption` | 図をキャプションのテキストブロックに紐づける。キャプションが無い図にはnullを指定する。どちらの場合も確認済みとして扱う。 |
| `merge_blocks` | 2つのテキストブロックを前者に統合し、後者を削除する。間に空白を入れるかは指定する。 |

orderはリスト順に適用され、各orderは直前までの結果に対して働く。見出しとして分類される
か、レベルを与えられた時点で、テキストブロックは `ProcessingBlockTextHeading` になる。

## エクスポート

全ページのスキャン後、`export_processing_blocks_to_ocr_result()` が平坦なブロック列を
`OcrResult` の木に変換する。読み順に走査し、

- 見出しはセクションを開く。ネスト先は、より小さいレベルで開いている最も内側の
  セクション。見出し自身はそのセクションの先頭ブロックになる。同レベル以下の見出しは
  内側にいないセクションを閉じるため、`1.` の下に `1.1` が入り、続く `2.` は `1.` の
  兄弟になる。
- それ以外は現在開いているセクションに追加する。最初の見出しより前のブロックは、
  ドキュメント自身であるルートセクションに入る。
- 図のキャプションブロックは図の `caption` に畳み込まれ、独立したブロックとしては
  出力しない。キャプションのテキストが重複しないようにするため。
- 各セクションの `existing_pages` は内容の和集合。`block_index` はドキュメント順に
  採番し、ルートが0。

ここでドキュメントを拒否することはない。ラベルの無いブロックは `paragraph` として、
レベルの無い見出しはセクションを開かずに、存在しないブロックを指すキャプションは破棄
して書き出す。いずれもログに警告を残す。ブロック1つのために実行全体を失う方が、
おかしなブロックが1つ混じるより悪いため。

## 規約

- Blockerが画像または表として検出したブロックは、最初から `figure` / `table` として
  ラベル付けされた状態で始まる。検出結果が答えなので、オーガナイザには実際に判断すべき
  ブロックだけが残る。
- 変数として保持するページは全て0始まりのindexで、名前は `page_index`（`scan_page` の
  引数も `ProcessingBlock.page_index` も同様）。`+ 1` するのは表示する箇所だけ——プロンプト、
  画像のラベル、ブロック状態JSON、ログ。読み手は1からページを数えるため。モデルに見せる
  JSONでフィールド名が `page_number` なのも同じ理由。
- モデルに見せたJSONに存在するidのみ使用でき、未知のidを指すorderは無視ではなく却下する。
- プロンプトおよびモデル向けのテキストは全て英語。
