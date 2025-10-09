import requests
from bs4 import BeautifulSoup
import PyPDF2
import io

def fetch_text_from_url(url: str) -> str:
    """
    Fetches and cleans text content from a webpage URL.
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # remove unwanted tags
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
            tag.extract()

        # get visible text
        text = soup.get_text(separator=" ", strip=True)

        # collapse multiple spaces
        clean_text = " ".join(text.split())

        # limit to avoid sending huge data to AI
        return clean_text[:5000]
    except Exception as e:
        return f"Could not extract content from {url}: {e}"


def extract_text_from_pdf(file) -> str:
    """
    Extract text from an uploaded PDF file.
    `file` should be Django's InMemoryUploadedFile or TemporaryUploadedFile
    """
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return " ".join(text.split())[:5000]  # limit to 5000 chars
    except Exception as e:
        return f"Could not extract text from PDF: {e}"

def incorrect_answer(quiz, attempt):
    total_questions = quiz.questions.count()
    if not attempt:
        return total_questions
    return total_questions - attempt.score