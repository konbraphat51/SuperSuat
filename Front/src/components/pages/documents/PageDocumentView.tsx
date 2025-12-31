import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
	fetchDocument,
	fetchDocumentPages,
	fetchHighlights,
	createHighlight,
	updateHighlight,
	deleteHighlight,
	type DocumentMetadata,
	type PageData,
	type HighlightData,
	type ParagraphData,
} from "../../../scripts/FirebaseClient";

// Styles
const styles = {
	container: {
		display: "flex",
		height: "calc(100vh - 120px)",
		padding: "20px",
		gap: "20px",
	} as React.CSSProperties,
	mainContent: {
		flex: 1,
		overflowY: "auto",
		padding: "20px",
		backgroundColor: "#fff",
		borderRadius: "8px",
		border: "1px solid #ddd",
	} as React.CSSProperties,
	sidebar: {
		width: "350px",
		overflowY: "auto",
		padding: "20px",
		backgroundColor: "#f9f9f9",
		borderRadius: "8px",
		border: "1px solid #ddd",
	} as React.CSSProperties,
	header: {
		padding: "20px",
		borderBottom: "1px solid #ddd",
		backgroundColor: "#f5f5f5",
	} as React.CSSProperties,
	paragraph: {
		padding: "12px 16px",
		marginBottom: "8px",
		borderRadius: "4px",
		lineHeight: 1.8,
		cursor: "text",
		position: "relative",
		transition: "background-color 0.2s",
	} as React.CSSProperties,
	highlightCard: {
		padding: "16px",
		marginBottom: "12px",
		borderRadius: "8px",
		border: "1px solid #ddd",
		backgroundColor: "#fff",
		cursor: "pointer",
		transition: "box-shadow 0.2s",
	} as React.CSSProperties,
};

// Helper to convert RGB array to CSS color
const rgbToColor = (rgb: [number, number, number], alpha = 0.4) =>
	`rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;

// Highlight colors available
const HIGHLIGHT_COLORS: [number, number, number][] = [
	[255, 255, 0], // Yellow
	[0, 255, 0], // Green
	[0, 255, 255], // Cyan
	[255, 192, 203], // Pink
	[255, 165, 0], // Orange
];

interface HighlightCardProps {
	highlight: HighlightData;
	paragraph?: ParagraphData;
	isSelected: boolean;
	onSelect: () => void;
	onMemoChange: (memo: string) => void;
	onDelete: () => void;
}

const HighlightCard = ({
	highlight,
	paragraph,
	isSelected,
	onSelect,
	onMemoChange,
	onDelete,
}: HighlightCardProps) => {
	const [isEditing, setIsEditing] = useState(false);
	const [memo, setMemo] = useState(highlight.memo);

	const highlightedText = paragraph
		? paragraph.content.substring(highlight.startOffset, highlight.endOffset)
		: "";

	const handleSaveMemo = () => {
		onMemoChange(memo);
		setIsEditing(false);
	};

	return (
		<div
			style={{
				...styles.highlightCard,
				borderLeft: `4px solid ${rgbToColor(highlight.color, 1)}`,
				boxShadow: isSelected ? "0 4px 12px rgba(0,0,0,0.15)" : "none",
			}}
			onClick={onSelect}
		>
			<div
				style={{
					fontSize: "14px",
					color: "#333",
					marginBottom: "8px",
					padding: "8px",
					backgroundColor: rgbToColor(highlight.color, 0.2),
					borderRadius: "4px",
					maxHeight: "60px",
					overflow: "hidden",
					textOverflow: "ellipsis",
				}}
			>
				{highlightedText || "..."}
			</div>

			{isEditing ? (
				<div>
					<textarea
						value={memo}
						onChange={(e) => setMemo(e.target.value)}
						style={{
							width: "100%",
							minHeight: "80px",
							padding: "8px",
							border: "1px solid #ddd",
							borderRadius: "4px",
							resize: "vertical",
							fontFamily: "inherit",
							fontSize: "14px",
						}}
						placeholder="メモを入力..."
						onClick={(e) => e.stopPropagation()}
					/>
					<div style={{ marginTop: "8px", display: "flex", gap: "8px" }}>
						<button
							onClick={(e) => {
								e.stopPropagation();
								handleSaveMemo();
							}}
							style={{
								padding: "6px 12px",
								backgroundColor: "#4a90d9",
								color: "#fff",
								border: "none",
								borderRadius: "4px",
								cursor: "pointer",
							}}
						>
							保存
						</button>
						<button
							onClick={(e) => {
								e.stopPropagation();
								setIsEditing(false);
								setMemo(highlight.memo);
							}}
							style={{
								padding: "6px 12px",
								backgroundColor: "#ddd",
								color: "#333",
								border: "none",
								borderRadius: "4px",
								cursor: "pointer",
							}}
						>
							キャンセル
						</button>
					</div>
				</div>
			) : (
				<div>
					<div
						style={{
							fontSize: "14px",
							color: highlight.memo ? "#333" : "#999",
							minHeight: "20px",
						}}
					>
						{highlight.memo || "クリックしてメモを追加"}
					</div>
					<div
						style={{ marginTop: "8px", display: "flex", gap: "8px" }}
						onClick={(e) => e.stopPropagation()}
					>
						<button
							onClick={() => setIsEditing(true)}
							style={{
								padding: "4px 8px",
								fontSize: "12px",
								backgroundColor: "#f0f0f0",
								border: "1px solid #ddd",
								borderRadius: "4px",
								cursor: "pointer",
							}}
						>
							編集
						</button>
						<button
							onClick={onDelete}
							style={{
								padding: "4px 8px",
								fontSize: "12px",
								backgroundColor: "#fee",
								border: "1px solid #fcc",
								borderRadius: "4px",
								cursor: "pointer",
								color: "#c00",
							}}
						>
							削除
						</button>
					</div>
				</div>
			)}
		</div>
	);
};

interface ParagraphWithHighlightsProps {
	paragraph: ParagraphData;
	highlights: HighlightData[];
	selectedHighlightId: string | null;
	onAddHighlight: (
		paragraphIndex: number,
		startOffset: number,
		endOffset: number
	) => void;
	onHighlightClick: (highlightId: string) => void;
}

const ParagraphWithHighlights = ({
	paragraph,
	highlights,
	selectedHighlightId,
	onAddHighlight,
	onHighlightClick,
}: ParagraphWithHighlightsProps) => {
	const handleMouseUp = () => {
		const selection = window.getSelection();
		if (!selection || selection.isCollapsed) return;

		const selectedText = selection.toString();
		if (!selectedText.trim()) return;

		// Get the selection range relative to the paragraph content
		const range = selection.getRangeAt(0);
		const container = range.commonAncestorContainer;

		// Find the paragraph element
		let paragraphElement = container.parentElement;
		while (
			paragraphElement &&
			!paragraphElement.getAttribute("data-paragraph-index")
		) {
			paragraphElement = paragraphElement.parentElement;
		}

		if (!paragraphElement) return;

		// Calculate offsets within the paragraph text
		const paragraphIndex = parseInt(
			paragraphElement.getAttribute("data-paragraph-index") || "0"
		);

		// Get text content before selection
		const fullText = paragraph.content;
		const startOffset = fullText.indexOf(selectedText);
		const endOffset = startOffset + selectedText.length;

		if (startOffset >= 0 && endOffset <= fullText.length) {
			onAddHighlight(paragraphIndex, startOffset, endOffset);
			selection.removeAllRanges();
		}
	};

	// Render text with highlights
	const renderHighlightedText = () => {
		const content = paragraph.content;
		const paragraphHighlights = highlights.filter(
			(h) => h.paragraphIndex === paragraph.paragraph_index
		);

		if (paragraphHighlights.length === 0) {
			return content;
		}

		// Sort highlights by start offset
		const sortedHighlights = [...paragraphHighlights].sort(
			(a, b) => a.startOffset - b.startOffset
		);

		const parts: React.ReactNode[] = [];
		let lastIndex = 0;

		sortedHighlights.forEach((highlight) => {
			// Add text before highlight
			if (highlight.startOffset > lastIndex) {
				parts.push(content.substring(lastIndex, highlight.startOffset));
			}

			// Add highlighted text
			const isSelected = highlight.id === selectedHighlightId;
			parts.push(
				<span
					key={highlight.id}
					style={{
						backgroundColor: rgbToColor(highlight.color, isSelected ? 0.6 : 0.4),
						cursor: "pointer",
						borderRadius: "2px",
						padding: "0 2px",
						transition: "background-color 0.2s",
					}}
					onClick={() => onHighlightClick(highlight.id)}
				>
					{content.substring(highlight.startOffset, highlight.endOffset)}
				</span>
			);

			lastIndex = highlight.endOffset;
		});

		// Add remaining text
		if (lastIndex < content.length) {
			parts.push(content.substring(lastIndex));
		}

		return parts;
	};

	const roleStyles: Record<string, React.CSSProperties> = {
		title: { fontSize: "24px", fontWeight: "bold", marginBottom: "16px" },
		sectionHeading: {
			fontSize: "20px",
			fontWeight: "bold",
			marginTop: "24px",
			marginBottom: "12px",
		},
		pageHeader: { fontSize: "12px", color: "#666" },
		pageFooter: { fontSize: "12px", color: "#666" },
		pageNumber: { fontSize: "12px", color: "#666", textAlign: "right" },
	};

	return (
		<div
			data-paragraph-index={paragraph.paragraph_index}
			style={{
				...styles.paragraph,
				...(roleStyles[paragraph.role] || {}),
				backgroundColor:
					highlights.some(
						(h) =>
							h.paragraphIndex === paragraph.paragraph_index &&
							h.id === selectedHighlightId
					)
						? "#f0f7ff"
						: "transparent",
			}}
			onMouseUp={handleMouseUp}
		>
			{renderHighlightedText()}
		</div>
	);
};

export const PageDocumentView = () => {
	const { documentId } = useParams<{ documentId: string }>();
	const [document, setDocument] = useState<DocumentMetadata | null>(null);
	const [pages, setPages] = useState<PageData[]>([]);
	const [highlights, setHighlights] = useState<HighlightData[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [selectedHighlightId, setSelectedHighlightId] = useState<string | null>(
		null
	);
	const [currentColorIndex, setCurrentColorIndex] = useState(0);

	// Load document data
	useEffect(() => {
		const loadData = async () => {
			if (!documentId) return;

			try {
				setLoading(true);
				setError(null);

				const [docData, pagesData, highlightsData] = await Promise.all([
					fetchDocument(documentId),
					fetchDocumentPages(documentId),
					fetchHighlights(documentId),
				]);

				if (!docData) {
					setError("ドキュメントが見つかりません");
					return;
				}

				setDocument(docData);
				setPages(pagesData);
				setHighlights(highlightsData);
			} catch (err) {
				console.error("Error loading document:", err);
				setError("ドキュメントの読み込みに失敗しました");
			} finally {
				setLoading(false);
			}
		};

		loadData();
	}, [documentId]);

	// Get all paragraphs sorted by paragraph_index
	const allParagraphs = pages
		.flatMap((page) => page.paragraphs)
		.sort((a, b) => a.paragraph_index - b.paragraph_index);

	const handleAddHighlight = useCallback(
		async (paragraphIndex: number, startOffset: number, endOffset: number) => {
			if (!documentId) return;

			try {
				const color = HIGHLIGHT_COLORS[currentColorIndex];
				const highlightId = await createHighlight(documentId, {
					paragraphIndex,
					startOffset,
					endOffset,
					color,
					memo: "",
				});

				const newHighlight: HighlightData = {
					id: highlightId,
					documentId,
					paragraphIndex,
					startOffset,
					endOffset,
					color,
					memo: "",
				};

				setHighlights((prev) => [...prev, newHighlight]);
				setSelectedHighlightId(highlightId);

				// Cycle to next color
				setCurrentColorIndex((prev) => (prev + 1) % HIGHLIGHT_COLORS.length);
			} catch (err) {
				console.error("Error creating highlight:", err);
			}
		},
		[documentId, currentColorIndex]
	);

	const handleUpdateHighlightMemo = useCallback(
		async (highlightId: string, memo: string) => {
			if (!documentId) return;

			try {
				await updateHighlight(documentId, highlightId, { memo });
				setHighlights((prev) =>
					prev.map((h) => (h.id === highlightId ? { ...h, memo } : h))
				);
			} catch (err) {
				console.error("Error updating highlight:", err);
			}
		},
		[documentId]
	);

	const handleDeleteHighlight = useCallback(
		async (highlightId: string) => {
			if (!documentId) return;

			try {
				await deleteHighlight(documentId, highlightId);
				setHighlights((prev) => prev.filter((h) => h.id !== highlightId));
				if (selectedHighlightId === highlightId) {
					setSelectedHighlightId(null);
				}
			} catch (err) {
				console.error("Error deleting highlight:", err);
			}
		},
		[documentId, selectedHighlightId]
	);

	if (loading) {
		return (
			<div
				style={{ padding: "40px", textAlign: "center", color: "#666" }}
			>
				読み込み中...
			</div>
		);
	}

	if (error) {
		return (
			<div style={{ padding: "20px" }}>
				<div
					style={{
						padding: "20px",
						backgroundColor: "#fee",
						borderRadius: "8px",
						color: "#c00",
						marginBottom: "20px",
					}}
				>
					{error}
				</div>
				<Link to="/documents" style={{ color: "#4a90d9" }}>
					← ドキュメント一覧に戻る
				</Link>
			</div>
		);
	}

	return (
		<div>
			<div style={styles.header}>
				<Link
					to="/documents"
					style={{
						color: "#4a90d9",
						textDecoration: "none",
						marginBottom: "8px",
						display: "inline-block",
					}}
				>
					← ドキュメント一覧
				</Link>
				<h1 style={{ margin: "8px 0 0 0", fontSize: "24px" }}>
					{document?.title || "Untitled"}
				</h1>
			</div>

			<div style={styles.container}>
				{/* Main content - Document paragraphs */}
				<div style={styles.mainContent}>
					<div
						style={{
							fontSize: "14px",
							color: "#666",
							marginBottom: "16px",
							padding: "8px",
							backgroundColor: "#f0f7ff",
							borderRadius: "4px",
						}}
					>
						💡 テキストを選択してハイライトを追加できます
					</div>

					{allParagraphs.map((paragraph) => (
						<ParagraphWithHighlights
							key={paragraph.paragraph_index}
							paragraph={paragraph}
							highlights={highlights}
							selectedHighlightId={selectedHighlightId}
							onAddHighlight={handleAddHighlight}
							onHighlightClick={setSelectedHighlightId}
						/>
					))}
				</div>

				{/* Sidebar - Highlight cards */}
				<div style={styles.sidebar}>
					<h2 style={{ margin: "0 0 16px 0", fontSize: "18px" }}>
						ハイライト ({highlights.length})
					</h2>

					{highlights.length === 0 ? (
						<div
							style={{
								color: "#666",
								fontSize: "14px",
								textAlign: "center",
								padding: "20px",
							}}
						>
							ハイライトがありません。
							<br />
							テキストを選択して追加してください。
						</div>
					) : (
						highlights
							.sort((a, b) => a.paragraphIndex - b.paragraphIndex)
							.map((highlight) => (
								<HighlightCard
									key={highlight.id}
									highlight={highlight}
									paragraph={allParagraphs.find(
										(p) => p.paragraph_index === highlight.paragraphIndex
									)}
									isSelected={selectedHighlightId === highlight.id}
									onSelect={() => setSelectedHighlightId(highlight.id)}
									onMemoChange={(memo) =>
										handleUpdateHighlightMemo(highlight.id, memo)
									}
									onDelete={() => handleDeleteHighlight(highlight.id)}
								/>
							))
					)}
				</div>
			</div>
		</div>
	);
};
