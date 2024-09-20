"""
"""
import os
import re
import json
import tiktoken
import subprocess

opj = os.path.join

BLUE = "\033[94m"
GREEN = "\033[92m"
ORANGE = "\033[93m"
RESET = "\033[0m"

# Cost in dollars per million tokens - https://openai.com/api/pricing/
COST_PER_MILLION_TOKENS = {
    'gpt-4o': (5.0, 15.0),
    'gpt-4o-2024-08-06': (2.5, 10.0),
    'gpt-4o-2024-05-13': (5.0, 15.0),
    'gpt-4o-mini': (0.150, 0.60),
    'gpt-4o-mini-2024-07-18': (0.150, 0.60),
    'o1-preview': (15.0, 60.0)
}

EMBEDDING_COST_PER_MILLION_TOKENS = {
    'text-embedding-3-small': 0.020,
    'text-embedding-3-large': 0.130,
    'ada v2': 0.10
}


def count_tokens(text: str, model: str = 'cl100k_base') -> int:
    """
    Count the tokens in the text using tiktoken.

    Args:
        text (str): The text to count the tokens for.
        model (str): The model to use. Defaults to 'cl100k_base'.
    Returns:
        int: The number of tokens in the text.
    """
    encoding = tiktoken.get_encoding(model)
    return len(encoding.encode(text))


def get_cost(input_text: str, output_text: str, model: str) -> float:
    """
    Get the cost of the input and output text.

    Args:
        input_text (str): The input text.
        output_text (str): The output text.
        model (str): The model to use.
    Returns:
        float: The cost of the input and output text.
    """
    input_cost_per_million, output_cost_per_million = COST_PER_MILLION_TOKENS[model]
    input_tokens = count_tokens(input_text)
    output_tokens = count_tokens(output_text)

    # Convert the cost per million tokens to the actual cost for the number of tokens
    total_input_cost = (input_tokens / 1_000_000) * input_cost_per_million
    total_output_cost = (output_tokens / 1_000_000) * output_cost_per_million

    # Return the total cost
    return total_input_cost + total_output_cost


def get_embedding_cost(num_tokens: int, model: str) -> float:
    """
    Calculate the cost of embedding tokens.

    Args:
        num_tokens (int): The number of tokens to embed.
        model (str): The model to use.
    Returns:
        float: The cost of the embedding.
    """
    cost_per_million_tokens = EMBEDDING_COST_PER_MILLION_TOKENS[model]
    return (num_tokens / 1_000_000) * cost_per_million_tokens


def get_color(name: str):
    if name.lower() == "user":
        return BLUE
    elif name.lower() == "counselor":
        return GREEN
    elif name.lower() == "suny":
        return ORANGE
    return ""


def chunk_pages(
        pages: list[str],
        chunk_size: int = 500,
        overlap_size: int = 125) -> list[dict]:
    """
    Split pages into chunks with a specified overlap size, including across pages,
    while preserving formatting.

    Args:
        pages (list[str]): A list of strings, each containing text from a page.
        chunk_size (int): The target size of each chunk in words. Defaults to 500.
        overlap_size (int): The number of words to overlap between chunks. Defaults to 125.

    Returns:
        list[dict]: A list of dictionaries, each containing the chunk text and metadata.
    """
    chunks = []
    all_tokens = []
    page_boundaries = [0]
    
    for page in pages:
        tokens = re.findall(r'\S+|\s+', page)
        all_tokens.extend(tokens)
        page_boundaries.append(page_boundaries[-1] + len(tokens))
    
    word_count = 0
    chunk_start = 0
    
    for i, token in enumerate(all_tokens):
        if not token.isspace():
            word_count += 1
        
        if word_count == chunk_size or i == len(all_tokens) - 1:
            chunk_text = ''.join(all_tokens[chunk_start:i+1])
            
            start_page = next(idx for idx, boundary in enumerate(page_boundaries) if boundary > chunk_start) - 1
            end_page = next(idx for idx, boundary in enumerate(page_boundaries) if boundary > i) - 1
            
            chunk_info = {
                "text": chunk_text,
                "metadata": {
                    "chunk_id": len(chunks),
                    "start_word": sum(1 for t in all_tokens[:chunk_start] if not t.isspace()),
                    "end_word": sum(1 for t in all_tokens[:i+1] if not t.isspace()) - 1,
                    "word_count": sum(1 for t in all_tokens[chunk_start:i+1] if not t.isspace()),
                    "start_page": start_page + 1,
                    "end_page": end_page + 1
                }
            }
            chunks.append(chunk_info)
            
            # Move back by overlap_size words for the next chunk
            while word_count > overlap_size and chunk_start < i:
                if not all_tokens[chunk_start].isspace():
                    word_count -= 1
                chunk_start += 1
    
    # If the last chunk is too small, merge it with the previous one
    if len(chunks) > 1 and chunks[-1]["metadata"]["word_count"] < chunk_size // 2:
        chunks[-2]["text"] += chunks[-1]["text"]
        chunks[-2]["metadata"]["end_word"] = chunks[-1]["metadata"]["end_word"]
        chunks[-2]["metadata"]["word_count"] += chunks[-1]["metadata"]["word_count"]
        chunks[-2]["metadata"]["end_page"] = chunks[-1]["metadata"]["end_page"]
        chunks.pop()

    return chunks


def chunk_text(text, chunk_size=500, overlap_size=125):
    """
    Split text into chunks with a specified overlap size, preserving formatting.

    Args:
        text (str): The input text to be chunked.
        chunk_size (int): The target size of each chunk in words. Defaults to 500.
        overlap_size (int): The number of words to overlap between chunks. Defaults to 125.

    Returns:
        list[dict]: A list of dictionaries, each containing the chunk text and metadata.
    """
    tokens = re.findall(r'\S+|\s+', text)
    chunks = []
    word_count = 0
    chunk_start = 0

    for i, token in enumerate(tokens):
        if not token.isspace():
            word_count += 1

        if word_count == chunk_size or i == len(tokens) - 1:
            chunk_text = ''.join(tokens[chunk_start:i+1])
            chunk_info = {
                "text": chunk_text,
                "metadata": {
                    "chunk_id": len(chunks),
                    "start_word": sum(1 for t in tokens[:chunk_start] if not t.isspace()),
                    "end_word": sum(1 for t in tokens[:i+1] if not t.isspace()) - 1,
                    "word_count": sum(1 for t in tokens[chunk_start:i+1] if not t.isspace())
                }
            }
            chunks.append(chunk_info)

            # Move back by overlap_size words for the next chunk
            while word_count > overlap_size and chunk_start < i:
                if not tokens[chunk_start].isspace():
                    word_count -= 1
                chunk_start += 1

    # If the last chunk is too small, merge it with the previous one
    if len(chunks) > 1 and chunks[-1]["metadata"]["word_count"] < chunk_size // 2:
        chunks[-2]["text"] += chunks[-1]["text"]
        chunks[-2]["metadata"]["end_word"] = chunks[-1]["metadata"]["end_word"]
        chunks[-2]["metadata"]["word_count"] += chunks[-1]["metadata"]["word_count"]
        chunks.pop()

    return chunks


def chunk_text_by_tokens(text: str, chunk_size: int = 512, overlap_size: int = 20) -> list[dict]:
    """
    Split text into chunks based on token count with a specified overlap,
    preserving formatting.

    Args:
        text (str): The input text to be chunked.
        chunk_size (int): The target size of each chunk in tokens.
        overlap_size (int): The number of tokens to overlap between chunks. Defaults to 125.

    Returns:
        list[dict]: A list of dictionaries, each containing the chunk text and metadata.
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    chunks = []
    chunk_start = 0

    while chunk_start < len(tokens):
        chunk_end = min(chunk_start + chunk_size, len(tokens))
        chunk_tokens = tokens[chunk_start:chunk_end]
        chunk_text = encoding.decode(chunk_tokens)

        chunk_info = {
            "text": chunk_text,
            "metadata": {
                "chunk_id": len(chunks),
                "start_token": chunk_start,
                "end_token": chunk_end - 1,
                "token_count": len(chunk_tokens)
            }
        }
        chunks.append(chunk_info)

        chunk_start += chunk_size - overlap_size

    # If the last chunk is too small, merge it with the previous one
    if len(chunks) > 1 and chunks[-1]["metadata"]["token_count"] < chunk_size // 2:
        last_chunk = chunks.pop()
        chunks[-1]["text"] += last_chunk["text"]
        chunks[-1]["metadata"]["end_token"] = last_chunk["metadata"]["end_token"]
        chunks[-1]["metadata"]["token_count"] += last_chunk["metadata"]["token_count"]

    return chunks


def find_all_pdfs(directory: str) -> list[str]:
    """
    Find all the PDFs in the directory.
    """
    pdf_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(opj(root, file))
    return pdf_files


def is_file_pdf(file_path: str) -> bool:
    try:
        # Note: We're not using text=True here anymore because it can fail
        result = subprocess.run(['file', file_path], capture_output=True, check=True)
        file_type_output = result.stdout.decode('utf-8', errors='ignore').strip()
        return 'PDF document' in file_type_output
    except subprocess.CalledProcessError as e:
        print(f"Error running 'file' command on {file_path}: {e}")
        return False
    except UnicodeDecodeError as e:
        print(f"Error decoding output for {file_path}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error checking file {file_path}: {e}")
        return False


def dict_to_str(info_dict: dict, format: bool) -> str:
    """
    Convert a dictionary to a string

    Args:
        info_dict (dict): The info dictionary

    Returns:
        info_str (str): The info string
    """
    info_str = ""
    for key, value in info_dict.items():
        if format:
            info_str += key.replace('_', ' ').title() + ": " + str(value) + "\n"
        else:
            info_str += key + ": " + str(value) + "\n"
    return info_str


def format_for_json(input_string):
    """
    Takes a string and formats it properly for use in JSON.
    Escapes special characters like quotes and newlines.
    """
    # Use json.dumps to handle escaping
    formatted_string = json.dumps(input_string)
    
    # Remove the surrounding double quotes added by json.dumps
    return formatted_string[1:-1]


def parse_json(message):
    """
    Parses a string as JSON, with special handling for the JSON format used by the agents.
    """
    try:
        return json.loads(message)
    except:
        print('Could not parse message as JSON')
        print(message)
        exit()