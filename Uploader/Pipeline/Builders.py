"""Building the OCR and the Leveler out of their settings."""

from Leveler.OcrResultLeveler import OcrResultLeveler
from OcrModule.MdWriter.Assembly.PageJoin import JoinJudge
from OcrModule.MdWriter.FigureCorrector.FigureCorrectionTool import (
    FigureCorrectionTool,
)
from OcrModule.MdWriter.FigureCorrector.FigureCorrector import FigureCorrector
from OcrModule.MdWriter.FigureDetector import FigureDetector
from OcrModule.MdWriter.MdWriterOcr import MdWriterOcr
from OcrModule.MdWriter.ReferenceReader import ReferenceReader
from OcrModule.MdWriter.Transcriber.PageTranscriber import PageTranscriber
from Pipeline.ChatModels import build_chat_model
from Pipeline.Settings import Detector, LevelSettings, OcrSettings, Reference

# One answer of the figure corrector is a short JSON list of boxes.
FIGURE_CORRECTOR_MAX_TOKENS = 4000


def build_md_writer_ocr(settings: OcrSettings) -> MdWriterOcr:
    """The MdWriter OCR the settings describe, its layout models loaded now."""
    model = build_chat_model(
        settings.provider,
        settings.model,
        settings.max_tokens,
        settings.reasoning_effort,
    )
    return MdWriterOcr(
        figure_detector=_build_detector(settings.detector),
        transcriber=PageTranscriber(
            model, figure_correction=_build_figure_correction(settings)
        ),
        join_judge=JoinJudge(model),
        reference_reader=_build_reference_reader(settings.reference),
        max_parallel_pages=settings.max_parallel,
    )


def build_leveler(settings: LevelSettings) -> OcrResultLeveler:
    """The Leveler the settings describe."""
    return OcrResultLeveler(
        build_chat_model(
            settings.provider,
            settings.model,
            settings.max_tokens,
            settings.reasoning_effort,
        )
    )


def _build_detector(detector: Detector) -> FigureDetector:
    """The figure detector named, its framework imported now."""
    if detector == "yomitoku":
        from OcrModule.MdWriter.FigureDetector.Yomitoku import YomitokuFigureDetector

        return YomitokuFigureDetector()
    if detector == "ppstructure":
        from OcrModule.MdWriter.FigureDetector.PpStructure import (
            PpStructureFigureDetector,
        )

        return PpStructureFigureDetector()

    from OcrModule.MdWriter.FigureDetector.DocLayoutYolo import (
        DocLayoutYoloFigureDetector,
    )

    return DocLayoutYoloFigureDetector()


def _build_reference_reader(reference: Reference) -> ReferenceReader | None:
    """The reference reader named, or None for none."""
    if reference == "none":
        return None

    from OcrModule.MdWriter.ReferenceReader.Yomitoku import YomitokuReferenceReader

    return YomitokuReferenceReader()


def _build_figure_correction(settings: OcrSettings) -> FigureCorrectionTool | None:
    """The correct_figures tool on the Bedrock corrector model, or None when
    the settings name no corrector."""
    if settings.figure_corrector_model is None:
        return None

    corrector_model = build_chat_model(
        "bedrock", settings.figure_corrector_model, FIGURE_CORRECTOR_MAX_TOKENS
    )
    return FigureCorrectionTool(
        FigureCorrector(corrector_model),
        max_call_count=settings.max_figure_corrections,
    )
