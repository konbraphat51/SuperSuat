# Blocker

ブロック分割OCRパイプラインの第1段階（[Plan.md](Plan.md) 参照）。ページ画像を受け取り、
読み取る価値のある領域を返す。ここでは文字認識を行わない。各ブロックのテキストは
第2段階で、ブロック単位で独立に読み取る。

English version: [Blocker.md](Blocker.md)

## 構造

```mermaid
classDiagram
    class Blocker {
        <<abstract>>
        +block(pages: list[Image]) BlockerResult
    }
    class YomitokuBlocker {
        -_device: str
        -_analyzer: LayoutAnalyzer
        +default_device() str
        +block(pages: list[Image]) BlockerResult
    }
    class BlockerResult {
        +blocks: list[Block]
    }
    class Block {
        +block_type: BlockType
        +page_number: int
        +bounding_box: tuple[int, int, int, int]
    }
    Blocker <|-- YomitokuBlocker
    YomitokuBlocker ..> BlockerResult
    BlockerResult *-- Block
```

パイプラインが依存するのは `Blocker` のみ。別のレイアウトモデルによる実装に差し替えても、
後続の段階には影響しない。

## YomitokuBlocker

[yomitoku](https://github.com/kotaro-kinoshita/yomitoku) の `LayoutAnalyzer`
（レイアウト解析と表構造認識を組み合わせたもの）を利用する。

```mermaid
sequenceDiagram
    participant Caller
    participant YomitokuBlocker
    participant LayoutAnalyzer
    Caller->>YomitokuBlocker: block(pages)
    loop 各ページ
        YomitokuBlocker->>YomitokuBlocker: PIL画像をBGR配列へ変換
        YomitokuBlocker->>LayoutAnalyzer: __call__(bgr_array)
        LayoutAnalyzer-->>YomitokuBlocker: paragraphs, figures, tables
        YomitokuBlocker->>YomitokuBlocker: Blockへ変換し上から下へ並べ替え
    end
    YomitokuBlocker-->>Caller: BlockerResult
```

### ブロック種別の対応

| yomitokuの要素 | `BlockType` |
| --- | --- |
| `paragraphs`（`section_headings`・`page_header`・`page_footer` ロールを含む） | `TEXT` |
| `figures` | `IMAGE` |
| `tables` | `TABLE` |

`BlockType.MATH` は出力されない。レイアウトモデルに数式カテゴリが無いため、数式を含む
ブロックは `TEXT` として返り、第3段階のLLMが判別する。

### 規約

- `page_number` はOCRモジュール全体と同様に0始まり。
- yomitokuの矩形は `[x1, y1, x2, y2]`、`Block.bounding_box` は
  `(x, y, width, height)`。
- 同一ページのブロックは上から下、次に左から右へ並べる。これは安定した順序であり、
  読み順ではない。読み順の推定は第3段階の役割。

### デバイス

`YomitokuBlocker()` はGPUが利用可能なら `cuda`、無ければ `cpu` を選ぶ。`device=` で
明示指定も可能。torchはCUDA 12.8のwheelインデックスから導入される
（`pyproject.toml` の `[tool.uv.sources]`）ため、`uv sync` でGPU対応版が入る。

モデルの重みは初回実行時にHugging Face Hubからダウンロードされ、キャッシュされる。
