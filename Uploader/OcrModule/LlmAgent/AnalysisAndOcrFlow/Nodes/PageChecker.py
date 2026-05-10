from pydantic import BaseModel, Field


SYSTEM_PROMPT = (
    "This entire project is to conduct OCR on scanned PDF documents. "
    "\nAn agent that have seen some pages of the document has analyzed the layout of the document,"
    " and created a layout document."
    "The actual OCR transcription agent will see only a single page of the document,"
    " and refer to this layout document to conduct OCR transcription on the page."
    "But this agent has not seen all pages, so the layout document may be incomplete."
    "\nYour role is to check whether the layout document have covered the layout of the single page given to you."
    "\nIf there is unknown layout style that may cause inconsistency in inter-page OCR results,"
    "specify and describe the unknown layout style so that the layout analyst agent can update the layout."
    "If all layout styles in the page are covered in the layout document, let the page pass."
    "You do not have to be too strict, but try not to miss any possible OCR inconsistency."
)

class OutputSchema(BaseModel):
    page_passed: bool = Field(
        description=(
            "Whether the page layout is covered in the layout document and can pass to OCR transcription."
        )
    )

    unknown_layout_styles: str | None = Field(
        description=(
            "If there is unknown layout style that may cause inconsistency in inter-page OCR results, "
            "specify and describe the unknown layout style so that the layout analyst agent can update the layout."
        )
    )
