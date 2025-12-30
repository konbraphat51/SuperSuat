# Docling PDF Processor

A Python module for processing PDF files using [Docling](https://github.com/DS4SD/docling), extracting OCR data, structure information, and exporting detected equations, figures, and tables as PNG images.

## Features

- **OCR Processing**: Extract text from scanned PDFs using Docling's OCR capabilities
- **Structure Detection**: Identify document structure including headings, paragraphs, lists
- **Image Extraction**: Export equations (formulas), figures, charts, and tables as PNG files
- **Reading Order**: Preserve the logical reading order of all document elements
- **JSON Output**: Generate structured JSON output with text content, labels, and image references

## Requirements

- Python 3.12+
- Docling (installed automatically with dependencies)
- Internet access on first run (to download model weights)

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
python -m Suat.Ocr.DoclingProcessor path/to/document.pdf

# With verbose logging
python -m Suat.Ocr.DoclingProcessor path/to/document.pdf -v
```

### Python API

```python
from Suat.Ocr.DoclingProcessor import process_pdf_to_folder, DoclingProcessor, ProcessorConfig

# Simple usage - creates output folder with same name as PDF
output_folder = process_pdf_to_folder("path/to/document.pdf")

# Advanced usage with custom configuration
config = ProcessorConfig(enable_ocr=True, images_scale=2.0)
processor = DoclingProcessor(config)
output = processor.process(pdf_path, output_dir)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCLING_ENABLE_OCR` | `true` | Enable/disable OCR processing |

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

The module follows SOLID principles with clear separation of concerns:

- `ProcessorConfig`: Configuration management
- `DocumentElement`: Base class for output elements (Single Responsibility)
- `LabelMapper`: Maps Docling labels to element types (Open/Closed)
- `ImageExporter`: Handles image export logic
- `ItemProcessor`: Processes individual document items
- `ConverterFactory`: Creates configured Docling converters
- `DoclingProcessor`: Main orchestrator class
- `OutputWriter`: Handles file output

## License

See the main project LICENSE file.
