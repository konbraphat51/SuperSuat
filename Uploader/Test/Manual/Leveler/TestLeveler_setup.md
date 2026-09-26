# TestLeveler 実行手順

保存済みの OCR 結果（`Input/<stem>.json`）を `OcrResultLeveler` にかけ、見出しを入れ子にした
文書ツリー・見出しのアウトライン・トークン数とコストを `Test/Manual/Leveler/Output/<実行名>/`
（`--run-name` がなければモデルID）に書き出す手動テストです。

English version: [TestLeveler_setup.en.md](TestLeveler_setup.en.md)

- 実際に OpenAI API を呼ぶため、**課金が発生します**
- ページ画像は `Test/Manual/Ocr/Sample/<stem>.pdf` を `Input/` を作ったときと同じ DPI（200）で描き直す

## 1. 入力

`Input/` には、3つのサンプル PDF を [TestMdWriter.py](../MdWriter/TestMdWriter.py) で読んだ結果を
保存してあります。MdWriter の出力なので、見出しはすべて1段です。

```bash
uv run python Test/Manual/MdWriter/TestMdWriter.py --detector yomitoku --provider openai --model gpt-6-sol --run-name leveler-input
```

| ファイル | 内容 |
| --- | --- |
| `<stem>.json` | 解析した `OcrResult`。Leveler への入力 |
| `<stem>.md` | モデルが書いた Markdown。見出しの確認用 |

入力を作り直すと `block_index` が変わるため、`GroundTruth/` も書き直す必要があります。

## 2. 実行

`Uploader/.env` に `OPENAI_API_KEY` を書いてから:

```bash
cd Uploader

# Input 内の全文書を gpt-6-sol で
uv run python Test/Manual/Leveler/TestLeveler.py

# 1文書だけ、別のモデルで
uv run python Test/Manual/Leveler/TestLeveler.py --input shido_math --model gpt-6-luna
```

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--input STEM` | Input 内の全文書 | 対象の `Input/<stem>.json`。複数回指定できる |
| `--model ID` | `gpt-6-sol` | OpenAI のモデルID |
| `--reasoning-effort LEVEL` | モデルの既定値 | 推論量 |
| `--max-tokens N` | `16000` | 1回の応答の最大トークン数（推論トークンを含む） |
| `--dpi N` | `200` | ページ画像の解像度。`Input/` を作ったときと揃える |
| `--run-name NAME` | モデルID | `Output/` の下の出力フォルダ名 |
| `--log-level LEVEL` | `INFO` | ログの詳細度 |
| `--log-file PATH` | `Output/TestLeveler.log` | ログの出力先（実行ごとに上書き） |

## 3. 出力と評価

```
Test/Manual/Leveler/Output/
├── TestLeveler.log
└── gpt-6-sol/
    ├── shido_math.json         # 入れ子にした OcrResult
    ├── shido_math.outline.txt  # 見出しをレベルで字下げしたアウトラインと評価
    └── shido_math.usage.txt    # トークン数とコスト
```

アウトラインの各行は `[block_index] p<ページ> L<レベル> 見出し` です。レベルは出力ツリーでの
深さなので、モデルがレベルを飛ばしても（1 → 3）深さは詰まります（1 → 2）。

`GroundTruth/<stem>.json` があれば、その `levels`（`block_index` → 正しい深さ）と比べます。
正解と違う行には `<-- expected N` が付きます。

| 指標 | 意味 |
| --- | --- |
| `levels` | 深さが正解と一致した見出しの割合 |
| `parents` | 直上の見出し（親）が正解と一致した見出しの割合。全体が1段ずれていても下がらない |
