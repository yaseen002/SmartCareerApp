import os
import pdfplumber
def extract_text_from_pdf(file_path):
    """
    Extracts text from a PDF file using pdfplumber.
    file_path: string path to the PDF file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    text = ""
    try:
        # ✅ Open the file using context manager
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise RuntimeError(f"Error reading PDF with pdfplumber: {str(e)}")

    return text.strip()