from markitdown import MarkItDown


def read_pdf(file_path: str):
    return MarkItDown().convert(file_path).text_content
