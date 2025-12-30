"""Configuration for PDF processing."""

from __future__ import annotations
import os
from dataclasses import dataclass
from enum import Enum

from docling.datamodel.pipeline_options import TableFormerMode


class AcceleratorDevice(str, Enum):
    """Supported accelerator devices."""
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"


@dataclass
class ProcessorConfig:
    """Configuration for PDF processing."""
    enable_ocr: bool = True
    table_mode: TableFormerMode = TableFormerMode.ACCURATE
    images_scale: float = 2.0
    accelerator: AcceleratorDevice = AcceleratorDevice.AUTO
    num_threads: int = 4

    @classmethod
    def from_env(cls) -> ProcessorConfig:
        """Create configuration from environment variables."""
        enable_ocr = os.environ.get("DOCLING_ENABLE_OCR", "true").lower() in ("true", "1", "yes", "on")
        
        # GPU configuration
        accelerator_str = os.environ.get("DOCLING_ACCELERATOR", "auto").lower()
        try:
            accelerator = AcceleratorDevice(accelerator_str)
        except ValueError:
            accelerator = AcceleratorDevice.AUTO
        
        # Thread configuration
        num_threads_str = os.environ.get("DOCLING_NUM_THREADS", "4")
        try:
            num_threads = int(num_threads_str)
        except ValueError:
            num_threads = 4
        
        return cls(enable_ocr=enable_ocr, accelerator=accelerator, num_threads=num_threads)

