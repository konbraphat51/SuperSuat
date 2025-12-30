"""Main processor for PDF documents using Docling."""

from __future__ import annotations
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    AcceleratorDevice as DoclingAccelerator,
    AcceleratorOptions,
)
from docling_core.types.doc import DocItemLabel

from .config import ProcessorConfig, AcceleratorDevice
from .models import (
    DocumentElement,
    DocumentOutput,
    ImageElement,
    LabelMapper,
    PageData,
    TextElement,
)
from .exporters import ImageExporter, ExportResult


class ConverterFactory:
    """Creates configured DocumentConverter instances."""
    
    @staticmethod
    def create(config: ProcessorConfig) -> DocumentConverter:
        """Create a DocumentConverter with the given configuration."""
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = config.enable_ocr
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.mode = config.table_mode
        pipeline_options.images_scale = config.images_scale
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        pipeline_options.generate_table_images = True
        
        # Configure accelerator (GPU support)
        accelerator_map = {
            AcceleratorDevice.AUTO: DoclingAccelerator.AUTO,
            AcceleratorDevice.CPU: DoclingAccelerator.CPU,
            AcceleratorDevice.CUDA: DoclingAccelerator.CUDA,
            AcceleratorDevice.MPS: DoclingAccelerator.MPS,
        }
        docling_accelerator = accelerator_map.get(config.accelerator, DoclingAccelerator.AUTO)
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=config.num_threads,
            device=docling_accelerator,
        )

        format_option = PdfFormatOption(pipeline_options=pipeline_options)
        return DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={InputFormat.PDF: format_option},
        )


class ItemProcessor:
    """Processes individual document items."""
    
    def __init__(self, image_exporter: ImageExporter, doc: Any):
        self._image_exporter = image_exporter
        self._doc = doc

    def process(self, item: Any, reading_order: int) -> DocumentElement | None:
        """Process a document item and return the appropriate element."""
        label = getattr(item, "label", DocItemLabel.TEXT)
        
        if LabelMapper.is_image_element(label):
            return self._create_image_element(item, label, reading_order)
        return self._create_text_element(item, label, reading_order)

    def _create_image_element(self, item: Any, label: DocItemLabel, reading_order: int) -> ImageElement:
        """Create an ImageElement from a document item."""
        element_type = LabelMapper.get_element_type(label)
        result = self._image_exporter.export(item, self._doc, element_type)
        return ImageElement(
            reading_order=reading_order,
            element_type=element_type,
            filename=result.filename,
            exported=result.success,
        )

    def _create_text_element(self, item: Any, label: DocItemLabel, reading_order: int) -> TextElement | None:
        """Create a TextElement from a document item."""
        content = self._extract_text_content(item)
        if not content:
            return None
        label_str = label.value if hasattr(label, "value") else str(label)
        return TextElement(reading_order=reading_order, content=content, label=label_str)

    @staticmethod
    def _extract_text_content(item: Any) -> str:
        """Extract text content from a document item."""
        if hasattr(item, "text") and item.text:
            return item.text
        if hasattr(item, "export_to_markdown"):
            return item.export_to_markdown()
        return ""

    @staticmethod
    def get_page_number(item: Any) -> int:
        """Extract page number from document item."""
        if hasattr(item, "prov") and item.prov:
            for prov in item.prov:
                if hasattr(prov, "page_no"):
                    return prov.page_no
        return 1


class DoclingProcessor:
    """Main processor for PDF documents using Docling."""
    
    def __init__(self, config: ProcessorConfig | None = None):
        self._config = config or ProcessorConfig.from_env()
        self._converter = ConverterFactory.create(self._config)

    def process(self, pdf_path: Path, output_dir: Path) -> DocumentOutput:
        """Process a PDF file and extract structured data."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result = self._converter.convert(str(pdf_path))
        doc = result.document
        
        image_exporter = ImageExporter(output_dir)
        item_processor = ItemProcessor(image_exporter, doc)
        
        page_elements: dict[int, list[DocumentElement]] = {}
        reading_order = 0

        for item, _ in doc.iterate_items():
            page_num = ItemProcessor.get_page_number(item)
            if page_num not in page_elements:
                page_elements[page_num] = []

            element = item_processor.process(item, reading_order)
            if element:
                page_elements[page_num].append(element)
            reading_order += 1

        output = DocumentOutput(source_pdf=pdf_path.name)
        for page_num in sorted(page_elements.keys()):
            output.pages.append(PageData(page_number=page_num, elements=page_elements[page_num]))
        
        return output
