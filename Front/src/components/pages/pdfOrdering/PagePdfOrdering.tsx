import PdfPageRenderer from "../../PdfPageRenderer";

export const PagePdfOrdering = () => {
	return (
		<div>
			<h1>PDF Ordering</h1>
			<PdfPageRenderer src="/sample.pdf" pageNumber={1} />
		</div>
	);
};
