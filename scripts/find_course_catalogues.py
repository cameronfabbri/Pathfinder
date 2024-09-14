"""
Script to find course catalogues in the data.
"""

import os
import json

from openai import OpenAI

from src.agent import Agent
from src.utils import find_all_pdfs

opj = os.path.join

BASE_PROMPT = """
Identify which PDFs are likely to contain information about academic programs,
including majors and minors, at the given SUNY school. Base your judgment solely
on the filenames, and prioritize files that suggest full course catalogs or
detailed program descriptions.

Your output must be in the following JSON format, without ``` or other code wrapping.

**Format:**

{
    "paths": [
        "filename1.pdf",
        "filename2.pdf",
        ...
    ]
}

**Filenames:**
"""

def process_pdf_chunk(agent: Agent, pdf_files: list[str]) -> list[str]:
    """
    Process a chunk of PDF files and return the paths to the course catalogues.

    Args:
        agent: The agent to use.
        pdf_files: The list of PDF files to process.

    Returns:
        The list of paths to the course catalogues.
    """
    prompt = BASE_PROMPT + '\n' + '\n'.join(pdf_files)
    agent.add_message('user', prompt)
    response = agent.invoke()
    content = response.choices[0].message.content
    agent.delete_last_message()
    try:
        return json.loads(content)['paths']
    except json.JSONDecodeError:
        print(f"Error decoding JSON: {content}")
        return []


def main():

    system_prompt = 'You are a helpful assistant that can find academic '
    system_prompt += 'course catalogues in the data.'

    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    agent = Agent(
        client,
        name="Agent",
        tools=None,
        model='gpt-4o-2024-08-06',
        system_prompt=system_prompt,
        json_mode=True
    )

    data_dir = opj('system_data', 'suny')

    for school in os.listdir(data_dir):
        school_dir = opj(data_dir, school)
        if not os.path.isdir(school_dir):
            continue

        catalogues_path = opj(school_dir, 'catalogues.txt')

        if os.path.exists(catalogues_path):
            print(f'Already processed {school}')
            continue

        pdf_files = find_all_pdfs(school_dir)

        print(f'Processing {school} with {len(pdf_files)} PDFs...')

        all_catalogues = []
        for i in range(0, len(pdf_files), 300):
            chunk = pdf_files[i:i+300]
            catalogues = process_pdf_chunk(agent, chunk)
            all_catalogues.extend(catalogues)
            print(f"Processed {i+len(chunk)}/{len(pdf_files)} PDFs")

        with open(catalogues_path, 'w') as f:
            for catalogue in all_catalogues:
                f.write(catalogue + '\n')

        print(f'Found {len(all_catalogues)} potential catalogues for {school}')
        print("---\n")


if __name__ == "__main__":
    main()