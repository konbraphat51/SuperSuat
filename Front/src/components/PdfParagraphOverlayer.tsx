import React, { useRef, useState } from "react";
import PdfPageRenderer, { type PdfPageRendererProps } from "./PdfPageRenderer";
import type { OcrData } from "../scripts/OcrData";

export interface PdfParagraphOverlayerProps {
    pdfRendererProps: PdfPageRendererProps;
    ocrData: OcrData;
    /** Background color for the overlay rectangles */
    overlayBackgroundColor?: string;
    /** Text color for the overlaid text */
    overlayTextColor?: string;
}

export const PdfParagraphOverlayer: React.FC<PdfParagraphOverlayerProps> = ({
    pdfRendererProps,
    ocrData,
    overlayBackgroundColor = "#ffffff",
    overlayTextColor = "#000000"
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [renderInfo, setRenderInfo] = useState<{
        width: number;
        height: number;
        scaleX: number;
        scaleY: number;
    } | null>(null);

    const handleRender = (info: { width: number; height: number }) => {
        // Find the OCR page data for the current page
        const currentPage = ocrData.pages.find(page => page.number === pdfRendererProps.pageNumber);
        if (currentPage) {
            // Calculate scale factors from OCR coordinates to rendered coordinates
            const scaleX = info.width / currentPage.width;
            const scaleY = info.height / currentPage.height;
            
            setRenderInfo({
                width: info.width,
                height: info.height,
                scaleX,
                scaleY
            });
        }
    };

    // Convert OCR polygon to bounding rectangle
    const polygonToBounds = (polygon: [number, number, number, number, number, number, number, number]) => {
        const xCoords = [polygon[0], polygon[2], polygon[4], polygon[6]];
        const yCoords = [polygon[1], polygon[3], polygon[5], polygon[7]];
        
        return {
            left: Math.min(...xCoords),
            top: Math.min(...yCoords),
            right: Math.max(...xCoords),
            bottom: Math.max(...yCoords)
        };
    };

    // Calculate optimal font size to fit text in rectangle
    const calculateFontSize = (text: string, width: number, height: number): number => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        if (!ctx) return 12;

        const maxFontSize = Math.min(width / 5, height / 1.2);
        const minFontSize = 8;

        // Binary search for optimal font size
        let low = minFontSize;
        let high = maxFontSize;
        
        while (high - low > 1) {
            const mid = (low + high) / 2;
            ctx.font = `${mid}px "Noto Sans JP", "Noto Sans", system-ui, sans-serif`;
            
            const words = text.split(' ');
            const lines: string[] = [];
            let currentLine = '';
            
            for (const word of words) {
                const testLine = currentLine ? `${currentLine} ${word}` : word;
                const metrics = ctx.measureText(testLine);
                
                if (metrics.width <= width * 0.9) { // Leave some padding
                    currentLine = testLine;
                } else {
                    if (currentLine) lines.push(currentLine);
                    currentLine = word;
                }
            }
            if (currentLine) lines.push(currentLine);
            
            const totalHeight = lines.length * mid * 1.2; // 1.2 is line height factor
            
            if (totalHeight <= height * 0.9) { // Leave some padding
                low = mid;
            } else {
                high = mid;
            }
        }
        
        return Math.max(low, minFontSize);
    };

    const renderOverlays = () => {
        if (!renderInfo) return null;

        const currentPage = ocrData.pages.find(page => page.number === pdfRendererProps.pageNumber);
        if (!currentPage) return null;

        return currentPage.paragraphs.map((paragraph, index) => {
            const bounds = polygonToBounds(paragraph.polygon);
            
            // Scale OCR coordinates to rendered coordinates
            const scaledBounds = {
                left: bounds.left * renderInfo.scaleX,
                top: bounds.top * renderInfo.scaleY,
                width: (bounds.right - bounds.left) * renderInfo.scaleX,
                height: (bounds.bottom - bounds.top) * renderInfo.scaleY
            };

            const fontSize = calculateFontSize(paragraph.content, scaledBounds.width, scaledBounds.height);

            return (
                <div
                    key={`paragraph-${paragraph.paragraph_index}-${index}`}
                    style={{
                        position: 'absolute',
                        left: scaledBounds.left,
                        top: scaledBounds.top,
                        width: scaledBounds.width,
                        height: scaledBounds.height,
                        backgroundColor: overlayBackgroundColor,
                        color: overlayTextColor,
                        fontSize: `${fontSize}px`,
                        fontFamily: '"Noto Sans JP", "Noto Sans", system-ui, sans-serif',
                        lineHeight: 1.2,
                        padding: '2px',
                        boxSizing: 'border-box',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        textAlign: 'center',
                        overflow: 'hidden',
                        wordWrap: 'break-word',
                        hyphens: 'auto',
                        pointerEvents: 'none' // Allow clicks to pass through
                    }}
                >
                    <div style={{ 
                        width: '100%', 
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}>
                        {paragraph.content}
                    </div>
                </div>
            );
        });
    };

    return (
        <div ref={containerRef} style={{ position: 'relative', display: 'inline-block' }}>
            <PdfPageRenderer 
                {...pdfRendererProps} 
                onRender={handleRender}
            />
            {renderOverlays()}
        </div>
    );
};
