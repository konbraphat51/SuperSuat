from dataclasses import dataclass

@dataclass
class ArticleRow:
    user_id: str
    article_id: str
    title: str
    tags: str
    pdf_file: str
    markdown_file: str
    ocr_file: str
