# OCR - Docling PDF Processor

A Python module for processing PDF files using [Docling](https://github.com/DS4SD/docling), extracting OCR data, structure information, and exporting detected equations, figures, and tables as PNG images.

## Features

- **OCR Processing**: Extract text from scanned PDFs using Docling's OCR capabilities
- **Structure Detection**: Identify document structure including headings, paragraphs, lists
- **Image Extraction**: Export equations (formulas), figures, charts, and tables as PNG files
- **Reading Order**: Preserve the logical reading order of all document elements
- **JSON Output**: Generate structured JSON output with text content, labels, and image references
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
DOCLING_ACCELERATOR=cuda uv run -m ocr path/to/document.pdf
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

## Architecture

The module follows SOLID principles with clear separation of concerns across multiple files:

```
ocr/
├── __init__.py      # Public API and exports
├── __main__.py      # CLI entry point
├── config.py        # ProcessorConfig, AcceleratorDevice
├── models.py        # Data models (TextElement, ImageElement, PageData, etc.)
├── exporters.py     # ImageExporter, OutputWriter
└── processor.py     # DoclingProcessor, ConverterFactory, ItemProcessor
```

- `ProcessorConfig`: Configuration management with GPU support
- `LabelMapper`: Maps Docling labels to element types (Open/Closed)
- `ImageExporter`: Handles image export logic
- `ItemProcessor`: Processes individual document items
- `ConverterFactory`: Creates configured Docling converters
- `DoclingProcessor`: Main orchestrator class
- `OutputWriter`: Handles file output

## License

See the main project LICENSE file.
