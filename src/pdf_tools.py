"""
Tools for working with PDFs.
"""

import os
import fitz
import PyPDF2
import pytesseract
import nest_asyncio

from PIL import Image
from openai import OpenAI
from llama_parse import LlamaParse
from PyPDF2 import PdfReader, PdfWriter


def is_pdf_searchable(pdf_path):
    """
    Check if a PDF is searchable or a scanned image.
    
    Args:
        pdf_path (str): Path to the PDF file.
    
    Returns:
        bool: True if the PDF is searchable, False if it's likely a scanned image.
    """
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        # Check the first few pages (adjust as needed)
        pages_to_check = min(3, len(reader.pages))
        
        for page_num in range(pages_to_check):
            page = reader.pages[page_num]
            
            # Check if the page has text
            if page.extract_text().strip():
                return True
            
            # Check if the page has images
            if '/XObject' in page['/Resources']:
                x_object = page['/Resources']['/XObject'].get_object()
                if x_object:
                    for obj in x_object:
                        if x_object[obj]['/Subtype'] == '/Image':
                            # If we find an image and no text, it's likely a scanned document
                            return False
    
    # If we haven't returned yet, assume it's searchable
    return True


def parse_text_from_image(image_path: str) -> str:
    """
    Parse text from an image using OCR.
    """
    return pytesseract.image_to_string(Image.open(image_path))


def load_pdf_text(file_path: str, page_start: int = 0, page_end: int = None) -> list[str]:
    """
    Convert a PDF file to a list of text strings, one for each page.

    Args:
        file_path (str): The path to the PDF file.
        page_start (int): The page number to start at. Defaults to 0.
        page_end (int): The page number to end at. Defaults to None.

    Returns:
        list[str]: A list of text strings, one for each page.
    """
    with open(file_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        texts = []
        for page_num in range(page_start, page_end if page_end else len(pdf_reader.pages)):
            page_text = pdf_reader.pages[page_num].extract_text()

            # Remove excessive whitespace and normalize line breaks
            cleaned_text = ' '.join(page_text.split())
            texts.append(cleaned_text)
    return texts


def parse_pdf_with_llama(pdf_file: str) -> str:
    """
    Load the text from a PDF file using llama_parse.

    Args:
        pdf_file (str): The path to the PDF file.

    Returns:
        str: The text from the PDF file.
    """

    nest_asyncio.apply()
    parser = LlamaParse(
        api_key=os.getenv("LLAMA_CLOUD_API_KEY"),  # can also be set in your env as LLAMA_CLOUD_API_KEY
        result_type="markdown",  # "markdown" and "text" are available
        num_workers=4,  # if multiple files passed, split in `num_workers` API calls
        verbose=True,
        language="en",  # Optionally you can define a language, default=en
    )

    return parser.load_data(pdf_file)


def extract_page(pdf_file: str, page_number: int, output_pdf: str) -> None:
    """
    Extract a single page from a PDF file and save it to a new PDF file.

    Args:
        pdf_file (str): The path to the PDF file.
        page_number (int): The page number to extract.
        output_pdf (str): The path to the output PDF file.
    Returns:
        None
    """
    reader = PdfReader(pdf_file)
    page = reader.pages[page_number]

    # Create a new PDF writer object and add the extracted page
    writer = PdfWriter()
    writer.add_page(page)

    # Write the extracted page to a new PDF
    with open(output_pdf, "wb") as output_file:
        writer.write(output_file)
    print(f"Extracted page {page_number} to {output_pdf}")


def get_pdf_metadata(path):
    with open(path, 'rb') as file:
        reader = PdfReader(file)
        metadata = reader.metadata
        if metadata:
            metadata_dict = {}
            for key, value in metadata.items():
                if hasattr(value, 'get_object'):
                    # Dereference the PDF object
                    value = value.get_object()
                if isinstance(value, (str, bytes)):
                    try:
                        # Try to decode if it's bytes, or encode and decode if it's str
                        value = value.encode('latin-1').decode('utf-8') if isinstance(value, str) else value.decode('utf-8')
                    except UnicodeDecodeError:
                        # If decoding fails, use the original value
                        pass
                metadata_dict[key] = value
            return metadata_dict
        else:
            return {}


def save_pdf_as_png(pdf_file: str, output_prefix: str) -> None:
    """
    Save a PNG image of each page in a PDF file.

    Args:
        pdf_file (str): The path to the PDF file.
        output_prefix (str): The prefix for the output PNG files.

    Returns:
        None
    """

    doc = fitz.open(pdf_file)
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
        # Use the actual dimensions of the pixmap
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image.save(f"{output_prefix}_{page.number + 1}.png", dpi=(300, 300))
    doc.close()


def parse_pdf_with_gpt(pdf_file: str, image_urls: list[str]) -> str:

    if os.path.exists('gpt-output.md'):
        with open('gpt-output.md', 'r') as f:
            return f.read()

    pdf_text = load_pdf_text(pdf_file)[0]
    client = OpenAI(api_key=os.environ.get("PATHFINDER_OPENAI_API_KEY"))

    image_urls = ['https://i.imgur.com/OPfinKX.png']

    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant that is an expert at parsing PDF documents. You will be given an image of a page from a PDF document and the extracted text. Your task is to extract the text from the image and return it as a string in markdown format. Do not include any other text in your response. Do not include ```markdown in your response."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": pdf_text
                },
            ] + [{"type": "image_url", "image_url": {"url": img_url}} for img_url in image_urls],
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=messages,
    )

    with open('gpt-output.md', 'w') as f:
        f.write(response.choices[0].message.content)

    return response.choices[0].message.content


def chunk_pages(pages, chunk_size=500, overlap_percentage=25):
    """
    Split pages into chunks with a specified overlap percentage, including across pages.

    Args:
        pages (list[str]): A list of strings, each containing text from a page.
        chunk_size (int): The target size of each chunk in words. Defaults to 500.
        overlap_percentage (int): The percentage of overlap between chunks. Defaults to 25.

    Returns:
        list[dict]: A list of dictionaries, each containing the chunk text and metadata.
    """
    chunks = []
    all_words = []
    page_boundaries = [0]  # Keep track of word indices where pages end
    
    for page in pages:
        page_words = page.split()
        all_words.extend(page_words)
        page_boundaries.append(page_boundaries[-1] + len(page_words))
    
    total_words = len(all_words)
    overlap_size = int(chunk_size * (overlap_percentage / 100))
    stride = chunk_size - overlap_size

    for i in range(0, total_words, stride):
        chunk_words = all_words[i:i + chunk_size]
        chunk_text = ' '.join(chunk_words)
        
        # Find start and end pages
        start_page = next(idx for idx, boundary in enumerate(page_boundaries) if boundary > i) - 1
        end_page = next(idx for idx, boundary in enumerate(page_boundaries) if boundary >= i + len(chunk_words)) - 1
        
        chunk_info = {
            "text": chunk_text,
            "metadata": {
                "chunk_id": len(chunks),
                "start_page": start_page,
                "end_page": end_page,
                "word_count": len(chunk_words)
            }
        }
        chunks.append(chunk_info)
    
    # If the last chunk is too small, merge it with the previous one
    if len(chunks) > 1 and chunks[-1]["metadata"]["word_count"] < chunk_size // 2:
        chunks[-2]["text"] += " " + chunks[-1]["text"]
        chunks[-2]["metadata"]["end_page"] = chunks[-1]["metadata"]["end_page"]
        chunks[-2]["metadata"]["word_count"] += chunks[-1]["metadata"]["word_count"]
        chunks.pop()

    return chunks
