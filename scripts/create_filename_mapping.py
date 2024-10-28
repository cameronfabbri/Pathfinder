"""
This script creates a mapping of the original filenames to the new filenames
for all the html files in the given directory (recursively).
"""
import os
import json
import re
import click

from tqdm import tqdm
from icecream import ic


def get_files(directory: str, extension: str) -> list[str]:
    """
    Recursively search for files with the given extension in the given directory and return their full paths.

    Args:
        directory (str): The root directory to start the search from.
        extension (str): File extension to search for.

    Returns:
        list[str]: A list of full paths to files with the given extension found in the directory and its subdirectories.
    """
    if not extension.startswith('.'):
        extension = '.' + extension

    result_files = []
    for root, _, filenames in os.walk(directory):
        for file in filenames:
            if file.lower().endswith(extension):
                result_files.append(os.path.join(root, file))

    return sorted(list(set(result_files)))

def sanitize_path(path: str) -> str:
    """
    Replace problematic characters in a path with underscores.
    """
    return re.sub(r'[?&:"=+]', '_', path)


def create_filename_mapping(directory: str, mapping_file: str):
    """
    Renames files in the specified directory to be Windows-compatible and
    creates a mapping file that stores the original and new filenames.

    Args:
        directory (str): Directory containing files to rename.
        mapping_file (str): Path to save the filename mapping.
    """
    # Load or initialize the filename mapping
    if os.path.exists(mapping_file):
        with open(mapping_file, 'r') as f:
            filepath_mapping = json.load(f)
    else:
        filepath_mapping = {}

    files = get_files(directory, '.html')
    files.extend(get_files(directory, '.pdf'))

    for filepath in tqdm(files):
        if '?' in filepath or '&' in filepath or '=' in filepath or '+' in filepath:

            # Sanitize the full path (including directories)
            sanitized_path = sanitize_path(filepath)
            
            if sanitized_path in filepath_mapping.values():
                continue

            # Ensure that each directory in the path exists
            if not os.path.exists(os.path.dirname(sanitized_path)):
                os.makedirs(os.path.dirname(sanitized_path), exist_ok=True)

            filepath_mapping[sanitized_path] = filepath

            os.rename(filepath, sanitized_path)

    # Save the mapping to a JSON file
    with open(mapping_file, 'w') as f:
        json.dump(filepath_mapping, f, indent=4)

    print(f"Mapping saved to {mapping_file}")


@click.command()
@click.option('--directory', '-d', required=True, help='Root directory to all universities.')
def main(directory):

    university_dirs = [os.path.join(directory, d) for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
    
    for dir in university_dirs:
        create_filename_mapping(dir, os.path.join(dir, 'filename_mapping.json'))


if __name__ == '__main__':
    main()
