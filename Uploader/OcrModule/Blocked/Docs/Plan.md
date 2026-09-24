1. レイアウト分析モデルでページ要素をブロック分け（バウンディングボックスのみ）
2. (並列) LLMで各ブロックの種別と読み順をページごとに推定し、その後まとめて見出しの階層構造を推定（[StructureOrganizer.ja.md](StructureOrganizer.ja.md)）
3. (並列) OCRモデルで各ブロックのテキストをテキスト化。ブロックの種別が確定しているので、表は表として読み、図は読まない（[Transcriber.ja.md](Transcriber.ja.md)）

3段階を通して実行する入口: [BlockedOcr.ja.md](BlockedOcr.ja.md)

English version: [Plan.en.md](Plan.en.md)
