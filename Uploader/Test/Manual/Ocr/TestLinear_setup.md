# TestLinear 実行手順

`Test/Manual/Ocr/Sample/` にある3つのPDF（`Seaman.pdf` / `shido_math.pdf` / `tate.pdf`）を
`LinearOcr` でOCRし、結果を `Test/Manual/Ocr/Output/<PDF名>.json` に書き出す手動テストです。

- プロバイダー: **Amazon Bedrock**（`ChatBedrockConverse`）
- OcrAgent / Clipper ともに **`qwen.qwen3-vl-235b-a22b`**
- 画像メッセージ形式: `build_image_message`（プロバイダー非依存の標準コンテンツブロック）

実際にBedrockのAPIを叩くため、**課金が発生します**。1ページごとにエージェントが複数回モデルを呼ぶので、
まずは `--max-pages 1` で1ページだけ試すことを推奨します。

---

## 1. Python環境

```bash
cd Uploader
uv sync
```

`langchain-aws` / `boto3` / `pymupdf` / `pillow` / `python-dotenv` はすべて `pyproject.toml` に入っているので、
追加インストールは不要です。

## 2. AWSアカウント側の準備

### 2-1. リージョンを決める

`qwen.qwen3-vl-235b-a22b` が提供されているリージョンを使う必要があります。
既定は `us-west-2` です。使えるかどうかは次のコマンドで確認できます。

```bash
aws bedrock list-foundation-models --region us-west-2 --query "modelSummaries[?contains(modelId,'qwen')].modelId"
```

> 東京リージョン（`ap-northeast-1`）ではQwenが提供されていないことがあります。
> ローカルの `~/.aws/config` のリージョン設定に関わらず、このスクリプトは既定で `us-west-2` を使います。

### 2-2. Bedrock APIキー（短期）を発行する

Bedrockコンソール → **API keys** → *Generate short-term API key* でキーを発行します。
短期キーは**最長12時間**で失効します。失効すると次のエラーになります。

```
AccessDeniedException: ... Bearer Token has expired
```

その場合はキーを再発行して `.env` を更新してください。

## 3. `.env` の設定

`Uploader/.env` に、発行したキーを置きます（`template.env` が雛形です）。

```env
AWS_BEDROCK_SHORT_API_KEY=<発行した短期APIキー>
```

必要に応じて次も指定できます（任意）。

```env
AWS_REGION=us-west-2
OCR_MODEL_ID=qwen.qwen3-vl-235b-a22b
CLIPPER_MODEL_ID=qwen.qwen3-vl-235b-a22b
```

> **IAMユーザーの通常のクレデンシャルを使いたい場合**
> `AWS_BEDROCK_SHORT_API_KEY` を設定しなければ、boto3の通常の解決順（環境変数 → `~/.aws/credentials` →
> プロファイル → インスタンスロール）にフォールバックします。必要な権限は `bedrock:InvokeModel` です。

## 4. 実行

```bash
cd Uploader

# Sample内の3点すべて
uv run python Test/Manual/Ocr/TestLinear.py

# まず1ページだけで動作確認（推奨）
uv run python Test/Manual/Ocr/TestLinear.py --max-pages 1

# 特定のPDFだけ
uv run python Test/Manual/Ocr/TestLinear.py --pdf tate.pdf --pdf shido_math.pdf
```

### オプション

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--pdf NAME` | Sample内の全PDF | 対象PDF。ファイル名でもパスでも可。複数回指定できる |
| `--dpi N` | `200` | ページ画像のレンダリング解像度。上げると小さい文字に強くなるが、送信する画像が重くなる |
| `--max-pages N` | 全ページ | 各PDFの先頭Nページだけ読む |
| `--ocr-model ID` | `qwen.qwen3-vl-235b-a22b` | OcrAgent用モデルID |
| `--clipper-model ID` | `qwen.qwen3-vl-235b-a22b` | Clipper用モデルID |
| `--region NAME` | `us-west-2` | Bedrockのリージョン |

## 5. 出力

`Test/Manual/Ocr/Output/` に、PDFごとに1つのJSONが出力されます。

```
Test/Manual/Ocr/Output/
├── Seaman.json
├── shido_math.json
└── tate.json
```

中身は `OcrResult` をそのままdict化したもので、`root_section` を根とする入れ子構造です。

```json
{
  "root_section": {
    "block_type": "section",
    "existing_pages": [0, 1],
    "block_index": 0,
    "section_content": [
      { "block_type": "heading", "existing_pages": [0], "block_index": 1, "text": "..." },
      { "block_type": "paragraph", "existing_pages": [0], "block_index": 2, "text": "..." },
      { "block_type": "figure", "existing_pages": [1], "block_index": 3,
        "page_number": 1, "bounding_box": [120, 340, 800, 460], "caption": "..." }
    ]
  }
}
```

`bounding_box` は `page_number` のページを `--dpi` でレンダリングしたときのピクセル座標
（`x, y, width, height`）なので、切り出すときは同じDPIでレンダリングし直してください。

1つのPDFが失敗しても残りは処理され、最後に失敗したファイル名が表示されて終了コード1になります。

---

## トラブルシューティング

| 症状 | 原因と対処 |
| --- | --- |
| `AccessDeniedException: Bearer Token has expired` | 短期APIキーの失効。再発行して `.env` を更新する |
| `AccessDeniedException: You don't have access to the model` | リージョン違い、またはIAMポリシー/SCPでモデル利用が制限されている（Model accessページは廃止済みのため事前の手動有効化は不要） |
| `ValidationException: ... model identifier is invalid` | そのリージョンでのモデルIDが違う。`aws bedrock list-foundation-models` で正しいIDを確認し、`--ocr-model` / `--clipper-model`（または `.env` の `OCR_MODEL_ID` / `CLIPPER_MODEL_ID`）に指定する。クロスリージョン推論プロファイル（`us.qwen....`）が必要な場合もある |
| `Missing Dependency: Using the login credential provider requires ... botocore[crt]` | ローカルの `~/.aws/config` が `login_session` プロファイルを使っている場合に出る。APIキー利用時はプロファイルを参照する必要がないので、スクリプト側で `AWS_CONFIG_FILE` を無効化して回避済み。IAMクレデンシャルで動かしたい場合は `uv pip install "botocore[crt]"` を実行する |
| `ThrottlingException` | Bedrock側のレート制限。時間を置くか `--max-pages` でページ数を絞る |
| `RuntimeError: Page N: agent stopped with pending tool calls` | エージェントが `RECURSION_LIMIT`（`OcrModule/Linear/OcrAgent.py`）に達した。ページが複雑すぎるか、モデルがツール呼び出しループに陥っている |
| `ModuleNotFoundError: No module named 'OcrModule'` | `uv run` を使わずに実行している。`Uploader` ディレクトリから `uv run python ...` で実行する |
