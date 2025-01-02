from markitdown import MarkItDown


def read_pdf(file_path: str):
    if not file_path.endswith('.pdf'):
        raise ValueError("File is not a PDF")
    return MarkItDown().convert(file_path).text_content

def read_docx(file_path: str):
    if not file_path.endswith('.docx'):
        raise ValueError("File is not a DOCX")
    return MarkItDown().convert(file_path).text_content

def read_excel(file_path: str):
    if not file_path.endswith('.xlsx'):
        raise ValueError("File is not an Excel file")
    return MarkItDown().convert(file_path).text_content

def read_mp3(file_path: str):
    if not file_path.endswith('.mp3'):
        raise ValueError("File is not an MP3")
    return MarkItDown().convert(file_path).text_content

def read_wav(file_path: str):
    if not file_path.endswith('.wav'):
        raise ValueError("File is not an WAV")
    return MarkItDown().convert(file_path).text_content
