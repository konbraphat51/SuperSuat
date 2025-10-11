import React, { useEffect, useRef, useState } from "react";
import PdfPageRenderer, { type PdfPageRendererProps } from "./PdfPageRenderer";
import type { OcrData } from "../scripts/OcrData";

export interface PdfParagraphOverlayerProps {
    pdfRendererProps: PdfPageRendererProps
    ocrData: OcrData
}

export const PdfParagraphOverlayer: React.FC<PdfParagraphOverlayerProps> = ({
    pdfRendererProps,
    ocrData
}) => {
    return (
        <PdfPageRenderer {...pdfRendererProps} />
    );
};
