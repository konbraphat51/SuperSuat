# PdfParagraphOverlayer Component

The `PdfParagraphOverlayer` component combines PDF rendering with OCR data to overlay text on top of the original PDF content. It renders a PDF page and overlays text paragraphs based on OCR coordinate data.

## Features

- Renders PDF pages using `PdfPageRenderer`
- Overlays text paragraphs from OCR data
- Automatic font sizing to fit text within detected regions
- Customizable overlay background and text colors
- Converts OCR polygon coordinates to bounding rectangles
- Scales coordinates from OCR space to rendered space

## Props

```typescript
interface PdfParagraphOverlayerProps {
    pdfRendererProps: PdfPageRendererProps;
    ocrData: OcrData;
    overlayBackgroundColor?: string; // Default: "#ffffff"
    overlayTextColor?: string;       // Default: "#000000"
}
```

### pdfRendererProps
Standard props passed to the underlying `PdfPageRenderer` component:
- `src`: PDF source (URL, ArrayBuffer, or Uint8Array)
- `pageNumber`: 1-based page number to render
- `scale`: Zoom factor (default: 1)
- `maxWidth`: Optional maximum width constraint
- `onRender`: Callback after render completes

### ocrData
OCR data structure containing pages with paragraph information:
```typescript
interface OcrData {
    pages: OcrPage[];
}

interface OcrPage {
    width: number;
    height: number;
    number: number;
    paragraphs: OcrParagraph[];
}

interface OcrParagraph {
    polygon: [number, number, number, number, number, number, number, number];
    role: string;
    content: string;
    paragraph_index: number;
}
```

## Usage Example

```typescript
import { PdfParagraphOverlayer } from './components/PdfParagraphOverlayer';
import type { OcrData } from './scripts/OcrData';

function MyComponent() {
    const [ocrData, setOcrData] = useState<OcrData | null>(null);
    
    useEffect(() => {
        fetch('/ocr.json')
            .then(response => response.json())
            .then(setOcrData);
    }, []);

    if (!ocrData) return <div>Loading...</div>;

    return (
        <PdfParagraphOverlayer
            pdfRendererProps={{
                src: "/path/to/document.pdf",
                pageNumber: 1,
                scale: 1.5,
                maxWidth: 800
            }}
            ocrData={ocrData}
            overlayBackgroundColor="#ffffff"
            overlayTextColor="#000000"
        />
    );
}
```

## How it Works

1. **PDF Rendering**: The component renders the PDF page using `PdfPageRenderer`
2. **Coordinate Scaling**: OCR coordinates are scaled from OCR space to rendered PDF space
3. **Polygon to Rectangle**: OCR polygon coordinates are converted to bounding rectangles
4. **Font Sizing**: Text is automatically sized to fit within detected regions using binary search
5. **Overlay Rendering**: Rectangles with background color are positioned over original text
6. **Text Rendering**: New text is rendered with proper centering and wrapping

## Key Features

### Automatic Font Sizing
The component automatically calculates the optimal font size for each text region:
- Uses binary search to find the largest font size that fits
- Considers both width and height constraints
- Accounts for line breaks and word wrapping
- Maintains minimum and maximum font size bounds

### Coordinate System Handling
- OCR coordinates are in the original document space
- Rendered coordinates depend on scale and maxWidth settings
- Component automatically calculates scale factors for accurate positioning

### Text Fitting Strategy
- Text is centered both horizontally and vertically within regions
- Long text automatically wraps to multiple lines
- Word breaking and hyphenation are supported
- Padding is applied to prevent text from touching edges

## Customization

### Colors
- `overlayBackgroundColor`: Background color for overlay rectangles (hides original text)
- `overlayTextColor`: Color for the overlaid text

### Styling
The component applies consistent styling:
- Font family: "Noto Sans JP", "Noto Sans", system-ui, sans-serif
- Line height: 1.2
- Text alignment: center
- Box sizing: border-box
- Overflow: hidden

## Performance Considerations

- Font size calculation uses canvas measurement for accuracy
- Binary search optimizes font sizing performance
- Overlay elements use absolute positioning for efficient rendering
- Pointer events are disabled on overlays to allow interaction with underlying PDF