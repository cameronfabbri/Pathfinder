"""
Script to scrape SUNY websites for information
"""

import json
import os
import subprocess

base_command = 'wget --mirror --convert-links --adjust-extension --page-requisites --no-parent'

def download_websites(json_file, reverse):
    # Read the JSON file
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Create the base directory if it doesn't exist
    base_dir = 'system_data/suny_schools/'
    os.makedirs(base_dir, exist_ok=True)

    if reverse:
        data = list(reversed(data))

    # Process each entry in the JSON file
    for entry in data:
        campus = entry['campus'].replace(' ', '-').replace('_', '').title()
        url = entry['campus_website']['url']
        
        # Create a folder for the campus
        campus_dir = os.path.join(base_dir, campus)

        os.makedirs(campus_dir, exist_ok=True)
        
        # Construct the wget command
        command = f"{base_command} -P {campus_dir} {url}"
       
        # Run the wget command
        print(f"Downloading {campus} website...")
        subprocess.run(command, shell=True)
        print(f"Finished downloading {campus} website.")

import sys
if __name__ == "__main__":
    reverse = False
    json_file = 'system_data/suny_general/suny_schools.json'
    if sys.argv[1] == 'reverse':
        reverse = True
    download_websites(json_file, reverse)