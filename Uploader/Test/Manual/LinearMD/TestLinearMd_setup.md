# TestLinearMd 実行手順

`Test/Manual/Ocr/Sample/` のPDFを `LinearMdOcr` にかけ、書き下したMarkdown・解析した文書ツリー・
図を描き込んだページ画像を `Test/Manual/LinearMD/Output/<detector>/` に書き出す手動テストです。

English version: [TestLinearMd_setup.en.md](TestLinearMd_setup.en.md)

- 図の検出: `doclayout`（DocLayout-YOLO）/ `yomitoku` / `ppstructure`（PP-StructureV3）。ローカルで実行
- 書き下し: OpenAI API または Amazon Bedrock のマルチモーダルモデル
- 実際にAPIを呼ぶため、**課金が発生します**。1回のリクエストで `BATCH_SIZE + 1` ページ分の画像を送るので、
  まずは `--max-pages 5 --batch-size 2`（リクエスト3回）で試すことを推奨します

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

# 5ページだけ、BATCH_SIZE=2で
uv run python Test/Manual/LinearMD/TestLinearMd.py --pdf shido_math.pdf --detector doclayout --batch-size 2 --max-pages 5

# Sample内の全PDFを既定の設定で
uv run python Test/Manual/LinearMD/TestLinearMd.py
```

### オプション

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--pdf NAME` | Sample内の全PDF | 対象PDF。ファイル名でもパスでも可。複数回指定できる |
| `--detector NAME` | `doclayout` | `doclayout` / `yomitoku` / `ppstructure` |
| `--batch-size N` | `4` | バッチの間隔。2以上 |
| `--max-parallel N` | `4` | 同時に送るバッチの最大数 |
| `--max-pages N` | 全ページ | 各PDFの先頭Nページだけ読む |
| `--dpi N` | `200` | ページ画像のレンダリング解像度 |
| `--provider NAME` | `OCR_PROVIDER` | `openai` / `bedrock` |
| `--model ID` | `OCR_MODEL_ID` | モデルID |
| `--max-tokens N` | `32000` | 1回の応答の最大トークン数。1回で複数ページを書くため大きめにしている |
| `--reasoning-effort LEVEL` | `OPENAI_REASONING_EFFORT` | OpenAIの推論モデルの推論量 |
| `--log-level LEVEL` | `INFO` | ログの詳細度 |
| `--log-file PATH` | `Output/TestLinearMd.log` | ログの出力先（実行ごとに上書き） |

## 4. 出力

```
Test/Manual/LinearMD/Output/
├── TestLinearMd.log     # モデルの応答・トークン数・検証エラーと再試行
└── doclayout/
    ├── Seaman.md        # 全バッチを結合したMarkdown（ページマーカー付き）
    ├── Seaman.json      # 解析した OcrResult
    └── Seaman/
        ├── page_0.png   # モデルに送ったページ画像（図の枠とIDを描画済み）
        └── ...
```

確認すること:

- PNGで、図にだけ枠とIDが付いていること
- `.md` で、バッチの境界（`BATCH_SIZE` の倍数のページ）の前後で文が重複したり抜けたりしていないこと
- `.json` の `existing_pages` と、図の `bounding_box` が正しいこと
- ログの `WARNING` に、検証エラーによる再試行が出ていないか（出ていれば、どの規則でつまずいたか）

## トラブルシューティング

| 症状 | 原因と対処 |
| --- | --- |
| `RuntimeError: batch N ... did not return usable Markdown` | 3回とも検証を通らなかった。ログの `WARNING` で理由を見る。`--batch-size` を下げると1回の負担が減る |
| `ValueError: batch_size must be at least 2` | `--batch-size` を2以上にする |
| 応答が途中で切れて検証エラーになる | `--max-tokens` を上げるか、`--batch-size` を下げる |
| `ERROR: OPENAI_API_KEY is not set.` | `.env` に `OPENAI_API_KEY` を書くか、`--provider bedrock` を使う |
