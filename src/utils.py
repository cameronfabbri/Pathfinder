"""
"""
import os
import json
import subprocess

opj = os.path.join


def find_all_pdfs(directory):
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