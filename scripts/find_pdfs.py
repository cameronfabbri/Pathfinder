"""
Some websites have PDFs that aren't saved with the .pdf extension. This script
finds all the files with missing extensions and renames the files.
"""

import os
import click
import shutil

from tqdm import tqdm

from src.utils import is_file_pdf

def count_directories(directory):
    return sum([len(dirs) for _, dirs, _ in os.walk(directory)])


@click.command()
@click.option("--directory", "-d", default=".", help="The directory to search for files.")
def main(directory: str):

    total_dirs = count_directories(directory)
    
    with tqdm(total=total_dirs, desc="Searching directories", unit="dir") as pbar:
        for root, dirs, files in os.walk(directory):
            pbar.update(1)
            for file in files:
                path = os.path.join(root, file)
                if is_file_pdf(path) and not path.endswith('.pdf'):
                    new_path = os.path.splitext(path)[0] + '.pdf'
                    shutil.copy2(path, new_path)
                    print(f"Renamed: {path} -> {new_path}\n")


if __name__ == "__main__":
    main()