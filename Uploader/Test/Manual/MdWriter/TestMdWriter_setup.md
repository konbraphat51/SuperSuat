# TestMdWriter 実行手順

`Test/Manual/Ocr/Sample/` のPDFを `MdWriterOcr` にかけ、書き下したMarkdown・解析した文書ツリー・
ページごとのトークン数とコスト・図を描き込んだページ画像を `Test/Manual/MdWriter/Output/<detector>/<model>/`
に書き出す手動テストです。

English version: [TestMdWriter_setup.en.md](TestMdWriter_setup.en.md)

- 図の検出: `doclayout`（DocLayout-YOLO）/ `yomitoku` / `ppstructure`（PP-StructureV3）。ローカルで実行
- 書き下し: OpenAI API または Amazon Bedrock のマルチモーダルモデル
- 実際にAPIを呼ぶため、**課金が発生します**。1回のリクエストで1ページ分の画像を送るので、
  まずは `--max-pages 5`（リクエスト5回と、あれば再試行分）で試すことを推奨します

## 1. Python環境

```bash
cd Uploader
uv sync
```

GPUとモデルの重みについては [TestBlocker_setup.md](../Blocked/TestBlocker_setup.md) と同じです。

## 2. APIキー

`Uploader/.env` に次を書きます（`template.env` を参照）。

| 変数 | 用途 |
| --- | --- |
| `OPENAI_API_KEY` | OpenAIで書き下すとき |
| `AWS_BEDROCK_SHORT_API_KEY` | Bedrockで書き下すとき（発行手順は [TestLinear_setup.md](../Ocr/TestLinear_setup.md)） |
| `OCR_PROVIDER` | `openai` / `bedrock`。既定は `openai` |
| `OCR_MODEL_ID` | モデルID。未指定ならプロバイダーごとの既定値 |

## 3. 実行

```bash
cd Uploader

# 5ページだけ
uv run python Test/Manual/MdWriter/TestMdWriter.py --pdf shido_math.pdf --detector doclayout --max-pages 5

# 既定のモデルの代わりに gpt-6-sol で
uv run python Test/Manual/MdWriter/TestMdWriter.py --detector yomitoku --provider openai --model gpt-6-sol

# Sample内の全PDFを既定の設定で
uv run python Test/Manual/MdWriter/TestMdWriter.py
```

### オプション

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--pdf NAME` | Sample内の全PDF | 対象PDF。ファイル名でもパスでも可。複数回指定できる |
| `--detector NAME` | `doclayout` | `doclayout` / `yomitoku` / `ppstructure` |
| `--max-parallel N` | `8` | 同時に送るページの最大数 |
| `--max-pages N` | 全ページ | 各PDFの先頭Nページだけ読む |
| `--dpi N` | `200` | ページ画像のレンダリング解像度 |
| `--provider NAME` | `OCR_PROVIDER` | `openai` / `bedrock` |
| `--model ID` | `OCR_MODEL_ID` | モデルID |
| `--max-tokens N` | `16000` | 1回の応答の最大トークン数（推論トークンを含む） |
| `--reasoning-effort LEVEL` | `OPENAI_REASONING_EFFORT` | OpenAIの推論モデルの推論量 |
| `--log-level LEVEL` | `INFO` | ログの詳細度 |
| `--log-file PATH` | `Output/TestMdWriter.log` | ログの出力先（実行ごとに上書き） |

## 4. 出力

```
Test/Manual/MdWriter/Output/
├── TestMdWriter.log         # モデルの応答・トークン数・検証エラーと再試行
└── doclayout/
    └── gpt-5.6-luna/
        ├── Seaman.md        # 全ページを結合したMarkdown（ページマーカー付き）
        ├── Seaman.json      # 解析した OcrResult
        ├── Seaman.usage.txt # ページごとのリクエスト数・トークン数・コスト
        └── Seaman/
            ├── page_0.png   # モデルに送ったページ画像（図の枠とIDを描画済み）
            └── ...
```

使用量の表は、PDFごとに処理が終わった時点でも表示します。`input` は入力トークンの総数、`cached` は
そのうちキャッシュから読んだ分、`output` は出力トークンの総数で、`reason` はそのうち推論に使った分です。
`reason` が0より大きければ、モデルのchain of thoughtが有効になっています。コストは `UsageCost.PRICING`
（100万トークンあたりのUSD）から計算し、そこに載っているモデルの場合だけ表示します。

| モデル | 入力 | キャッシュ済み入力 | キャッシュ書き込み | 出力 |
| --- | --- | --- | --- | --- |
| `gpt-6-luna` | $0.10 | $0.01 | $0.125 | $0.50 |
| `gpt-6-sol` | $2.00 | $0.20 | $2.50 | $10.00 |

確認すること:

- PNGで、図にだけ枠とIDが付いていること
- `.md` で、ページの変わり目の前後で文が重複したり抜けたりしていないこと
- `.json` の `existing_pages` と、図の `bounding_box` が正しいこと
- ログの `WARNING` に、検証エラーによる再試行が出ていないか（出ていれば、どの規則でつまずいたか）

## トラブルシューティング

| 症状 | 原因と対処 |
| --- | --- |
| `RuntimeError: page N ... did not return usable Markdown` | 3回とも検証を通らなかった。ログの `WARNING` で理由を見る |
| 応答が途中で切れて検証エラーになる | `--max-tokens` を上げる。推論トークンもこの上限に含まれる |
| `ERROR: OPENAI_API_KEY is not set.` | `.env` に `OPENAI_API_KEY` を書くか、`--provider bedrock` を使う |
