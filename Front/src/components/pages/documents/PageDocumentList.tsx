import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
	fetchDocuments,
	type DocumentMetadata,
} from "../../../scripts/FirebaseClient";

export const PageDocumentList = () => {
	const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		const loadDocuments = async () => {
			try {
				setLoading(true);
				setError(null);
				const docs = await fetchDocuments();
				setDocuments(docs);
			} catch (err) {
				console.error("Error loading documents:", err);
				setError("Failed to load documents. Please try again later.");
			} finally {
				setLoading(false);
			}
		};

		loadDocuments();
	}, []);

	const formatDate = (date?: Date) => {
		if (!date) return "-";
		return date.toLocaleDateString("ja-JP", {
			year: "numeric",
			month: "short",
			day: "numeric",
		});
	};

	return (
		<div style={{ padding: "20px", maxWidth: "1200px", margin: "0 auto" }}>
			<h1 style={{ marginBottom: "24px" }}>ドキュメント一覧</h1>

			{loading && (
				<div
					style={{
						textAlign: "center",
						padding: "40px",
						color: "#666",
					}}
				>
					読み込み中...
				</div>
			)}

			{error && (
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
			)}

			{!loading && !error && documents.length === 0 && (
				<div
					style={{
						textAlign: "center",
						padding: "40px",
						backgroundColor: "#f5f5f5",
						borderRadius: "8px",
						color: "#666",
					}}
				>
					ドキュメントがありません
				</div>
			)}

			{!loading && !error && documents.length > 0 && (
				<div
					style={{
						display: "grid",
						gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
						gap: "20px",
					}}
				>
					{documents.map((doc) => (
						<Link
							key={doc.id}
							to={`/documents/${doc.id}`}
							style={{
								textDecoration: "none",
								color: "inherit",
							}}
						>
							<div
								style={{
									border: "1px solid #ddd",
									borderRadius: "8px",
									padding: "20px",
									backgroundColor: "#fff",
									transition: "box-shadow 0.2s, transform 0.2s",
									cursor: "pointer",
								}}
								onMouseEnter={(e) => {
									e.currentTarget.style.boxShadow =
										"0 4px 12px rgba(0,0,0,0.1)";
									e.currentTarget.style.transform = "translateY(-2px)";
								}}
								onMouseLeave={(e) => {
									e.currentTarget.style.boxShadow = "none";
									e.currentTarget.style.transform = "translateY(0)";
								}}
							>
								<h3
									style={{
										margin: "0 0 12px 0",
										fontSize: "18px",
										color: "#333",
									}}
								>
									{doc.title}
								</h3>
								<div
									style={{
										fontSize: "14px",
										color: "#666",
									}}
								>
									<p style={{ margin: "4px 0" }}>
										ページ数: {doc.pageCount}
									</p>
									<p style={{ margin: "4px 0" }}>
										作成日: {formatDate(doc.createdAt)}
									</p>
								</div>
							</div>
						</Link>
					))}
				</div>
			)}
		</div>
	);
};
