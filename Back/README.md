# OCR - Docling PDF Processor

A Python module for processing PDF files using [Docling](https://github.com/DS4SD/docling), extracting OCR data, structure information, and exporting detected equations, figures, and tables as PNG images.

## Features

- **OCR Processing**: Extract text from scanned PDFs using Docling's OCR capabilities
- **Structure Detection**: Identify document structure including headings, paragraphs, lists
- **Hierarchy Preservation**: Maintain document hierarchy (sections, headings, nested content) as a tree structure
- **Image Extraction**: Export equations (formulas), figures, charts, and tables as PNG files
- **Reading Order**: Preserve the logical reading order of all document elements
- **Dual Output Format**: Generate both flat pages array and hierarchical structure in JSON
- **GPU Acceleration**: Support for NVIDIA CUDA and Apple Silicon (MPS) for faster processing

## Requirements

- Python 3.12+
- Docling (installed automatically with dependencies)
- Internet access on first run (to download model weights)
- (Optional) NVIDIA GPU with CUDA for accelerated processing

## Installation

```bash
cd Back
pip install -e .
```

Or using uv:

```bash
cd Back
uv sync
```

## Usage

### Command Line

```bash
# Basic usage
uv run -m ocr path/to/document.pdf

# With verbose logging
uv run -m ocr path/to/document.pdf -v

# Using NVIDIA GPU
uv run -m ocr path/to/document.pdf -a cuda

# Using Apple Silicon GPU
uv run -m ocr path/to/document.pdf -a mps

# Force CPU processing
uv run -m ocr path/to/document.pdf -a cpu
```

### Python API

```python
from ocr import process_pdf_to_folder, DoclingProcessor, ProcessorConfig, AcceleratorDevice

# Simple usage - creates output folder with same name as PDF
output_folder = process_pdf_to_folder("path/to/document.pdf")

# Advanced usage with custom configuration and GPU
config = ProcessorConfig(
    enable_ocr=True,
    images_scale=2.0,
    accelerator=AcceleratorDevice.CUDA  # Use NVIDIA GPU
)
processor = DoclingProcessor(config)
output = processor.process(pdf_path, output_dir)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCLING_ENABLE_OCR` | `true` | Enable/disable OCR processing |
| `DOCLING_ACCELERATOR` | `auto` | Accelerator device: `auto`, `cpu`, `cuda` (NVIDIA), `mps` (Apple Silicon) |
| `DOCLING_NUM_THREADS` | `4` | Number of threads for parallel processing |

## Output Structure

For a PDF file named `document.pdf`, the processor creates:

```
document/
├── output.json          # Structured data with text and references
├── equation_001.png     # Extracted formula images
├── equation_002.png
├── figure_001.png       # Extracted figures and charts
├── table_001.png        # Extracted table images
└── ...
```

## JSON Schema

The output JSON contains two main structures:
- **pages**: A flat array of elements organized by page number (preserves reading order)
- **hierarchy**: A tree structure representing the document's logical organization (sections, headings, etc.)

```json
{
  "source_pdf": "document.pdf",
  "pages": [
    {
      "page_number": 1,
      "elements": [
        {
          "type": "text",
          "content": "Document Title",
          "label": "title",
          "reading_order": 0
        },
        {
          "type": "figure",
          "filename": "figure_001.png",
          "reading_order": 1
        },
        {
          "type": "equation",
          "filename": "equation_001.png",
          "reading_order": 2
        },
        {
          "type": "table",
          "filename": "table_001.png",
          "reading_order": 3
        }
      ]
    }
  ],
  "hierarchy": [
    {
      "reading_order": 0,
      "label": "title",
      "content": "Document Title",
      "children": [
        {
          "reading_order": 1,
          "label": "section_header",
          "content": "Introduction",
          "children": [
            {
              "reading_order": 2,
              "label": "paragraph",
              "content": "This is the introduction text..."
            },
            {
              "reading_order": 3,
              "label": "picture",
              "type": "figure",
              "filename": "figure_001.png"
            }
          ]
        },
        {
          "reading_order": 4,
          "label": "section_header",
          "content": "Methods",
          "children": [
            {
              "reading_order": 5,
              "label": "paragraph",
              "content": "The methodology includes..."
            }
          ]
        }
      ]
    }
  ]
}
```

## Element Types

| Type | Description | Source Labels |
|------|-------------|---------------|
| `text` | Text content with label | All text elements |
| `equation` | Mathematical formulas | `formula` |
| `figure` | Images and charts | `picture`, `chart` |
| `table` | Data tables | `table` |

## Document Hierarchy

The hierarchy structure preserves the logical organization of the document as detected by Docling:

- **Tree Structure**: Nested nodes representing document organization (sections → headings → paragraphs → etc.)
- **Label-Based Hierarchy**: Uses Docling labels to determine nesting levels
  - `section_header`: Highest level sections
  - `title`: Document or section titles
  - `subtitle`: Subsections
  - `caption`, `page_header`, `page_footer`: Supporting elements
  - `paragraph`, `list_item`, etc.: Content nodes
- **Preserved Reading Order**: Each node retains its `reading_order` from the flat pages array
- **Mixed Content**: Text and image elements can appear at any hierarchy level

### Hierarchy Levels

The hierarchy builder organizes elements by their labels:

| Level | Labels | Description |
|-------|--------|-------------|
| 0 | `section_header` | Top-level sections |
| 1 | `title` | Document/section titles |
| 2 | `subtitle` | Subsection headers |
| 3 | `caption`, `header` (non-page) | Supporting headers |
| 4 | `page_header`, `page_footer` | Page-level elements |
| 100 | All others | Leaf nodes (paragraphs, images, etc.) |

## Architecture

The module follows SOLID principles with clear separation of concerns across multiple files:

```
ocr/
├── __init__.py      # Public API and exports
├── __main__.py      # CLI entry point
├── config.py        # ProcessorConfig, AcceleratorDevice
├── models.py        # Data models (TextElement, ImageElement, HierarchyNode, PageData, etc.)
├── exporters.py     # ImageExporter, OutputWriter
└── processor.py     # DoclingProcessor, ConverterFactory, ItemProcessor, HierarchyBuilder
```

- `ProcessorConfig`: Configuration management with GPU support
- `LabelMapper`: Maps Docling labels to element types (Open/Closed)
- `ImageExporter`: Handles image export logic
- `ItemProcessor`: Processes individual document items
- `HierarchyBuilder`: Constructs document hierarchy tree from items
- `ConverterFactory`: Creates configured Docling converters
- `DoclingProcessor`: Main orchestrator class
- `OutputWriter`: Handles file output

## License

See the main project LICENSE file.
