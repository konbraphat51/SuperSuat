# TestYomitoku 実行手順

`Test/Manual/Ocr/Sample/` のPDFを `YomitokuBlocker`（レイアウト解析のみ）にかけ、
検出したブロックを `Test/Manual/Blocked/Output/` に書き出す手動テストです。

English version: [TestYomitoku_setup.en.md](TestYomitoku_setup.en.md)

- モデル: yomitoku のレイアウト解析＋表構造認識（ローカル実行）
- **課金は発生しません**。外部APIは呼びません
- 文字認識は行いません。矩形と種別だけが出ます

## 1. Python環境

```bash
cd Uploader
uv sync
```

torchはCUDA 13.0のwheelインデックスから入ります（`pyproject.toml` の `[tool.uv.sources]`）。
NVIDIAのランタイムを含むため初回は数GBのダウンロードになります。

GPUが使えるかは次で確認できます。

```bash
uv run python -c "import torch; print(torch.cuda.is_available())"
```

`False` の場合はCPUで動きます（数倍遅くなるだけで、結果は変わりません）。
`--device cpu` で明示的にCPUを使うこともできます。

## 2. モデルの重み

初回実行時に Hugging Face Hub から自動でダウンロードされ、`~/.cache/huggingface/` に
キャッシュされます。認証は不要です。ネットワークが無い環境では失敗します。

## 3. 実行

```bash
cd Uploader

# Sample内の全PDF
uv run python Test/Manual/Blocked/TestYomitoku.py

# まず1ページだけ
uv run python Test/Manual/Blocked/TestYomitoku.py --max-pages 1

# 特定のPDFだけ、PNG出力なし
uv run python Test/Manual/Blocked/TestYomitoku.py --pdf tate.pdf --no-render
```

### オプション

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--pdf NAME` | Sample内の全PDF | 対象PDF。ファイル名でもパスでも可。複数回指定できる |
| `--dpi N` | `200` | ページ画像のレンダリング解像度 |
| `--max-pages N` | 全ページ | 各PDFの先頭Nページだけ読む |
| `--device NAME` | 自動 | `cuda` / `cpu` を明示指定する |
| `--no-render` | 無効 | 確認用PNGを出さず、JSONだけ書く |

## 4. 出力

```
Test/Manual/Blocked/Output/
├── tate.json       # BlockerResult をそのままJSON化したもの
├── tate_p0.png     # ページ画像に検出ブロックを重ねたもの
└── tate_p1.png
```

JSONは `BlockerResult` で、`bounding_box` は `(x, y, width, height)`、`page_number` は0始まりです。

```json
{
  "blocks": [
    { "block_type": "text", "page_number": 0, "bounding_box": [120, 340, 800, 460] },
    { "block_type": "table", "page_number": 0, "bounding_box": [130, 900, 780, 300] }
  ]
}
```

PNGではブロック種別ごとに枠の色が変わります（text=青 / math=赤 / image=緑 / table=橙）。
枠に振られた番号は、同一ページ内での並び順（上から下、次に左から右）です。

> `block_type` に `math` は現れません。レイアウトモデルに数式カテゴリが無いためです。
> 詳細は [Blocker.md](../../../OcrModule/Blocked/Docs/Blocker.md) を参照してください。

## トラブルシューティング

| 症状 | 原因と対処 |
| --- | --- |
| `ModuleNotFoundError: No module named 'OcrModule'` | `uv run` を使っていない。`Uploader` ディレクトリから `uv run python ...` で実行する |
| `torch.cuda.is_available()` が `False` | CPU版のtorchが入っている。`uv sync` をやり直す。NVIDIAドライバのCUDAバージョンが13.0未満の場合は `pyproject.toml` のインデックスを対応するもの（例: `cu128`）に変える |
| `CUDA out of memory` | `--dpi` を下げる、または `--device cpu` で実行する |
| 重みのダウンロードで止まる/失敗する | Hugging Face Hubへの接続を確認する。プロキシ環境では `HF_ENDPOINT` / `HTTPS_PROXY` を設定する |
