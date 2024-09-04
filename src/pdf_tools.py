import os
from openai import OpenAI
from PyPDF2 import PdfReader, PdfWriter
from getpass import getpass
from llama_parse import LlamaParse
from PIL import Image
import fitz
import nest_asyncio
import PyPDF2


def load_pdf_text(file_path, page_start=0, page_end=None):
    """
    Convert a PDF file to a list of text strings, one for each page.

    Args:
        file_path (str): The path to the PDF file.
        page_start (int): The page number to start at. Defaults to 0.
        page_end (int): The page number to end at. Defaults to None.

    Returns:
        list[str]: A list of text strings, one for each page.
    """
    pdf_file = open(file_path, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    texts = []
    for page_num in range(page_start, page_end if page_end else len(pdf_reader.pages)):
        texts.append(pdf_reader.pages[page_num].extract_text())
    pdf_file.close()
    return texts


def parse_pdf_with_llama(pdf_file):
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

    documents = parser.load_data(pdf_file)

    return documents[0].text


def extract_page(pdf_file, page_number, output_pdf):
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


def save_pdf_as_png(pdf_file, output_prefix):
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


def parse_pdf_with_gpt(pdf_file, image_urls):

    if os.path.exists('gpt-output.md'):
        with open('gpt-output.md', 'r') as f:
            return f.read()

    pdf_text = pdf_to_text(pdf_file)[0]
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