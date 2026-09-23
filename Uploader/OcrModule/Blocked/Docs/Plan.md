1. レイアウト分析モデルでページ要素をブロック分け
2. (並列) OCRモデルで各ブロックのテキストをテキスト化
3. (並列) LLMで読み順・ブロック種別をページごとに推定し、その後まとめて見出しの階層構造を推定（[StructureOrganizer.ja.md](StructureOrganizer.ja.md)）

English version: [Plan.en.md](Plan.en.md)
