"""
Script to scrape SUNY websites for information
"""

import os
import json
import subprocess

opj = os.path.join
base_command = 'wget2 --reject jpg,jpeg,png,gif,css,js,woff,woff2,svg --mirror --convert-links --adjust-extension --force-directories --page-requisites --no-parent --user-agent=Mozilla/5.0 --max-threads 9'

def main():

    with open('data/metadata.json', 'r') as f:
        data = json.load(f)

    downloaded = []
    with open('data/downloaded.txt', 'r') as f:
        downloaded = f.readlines()
    downloaded = [x.strip() for x in downloaded]

    for university_name, urls in data.items():
        if university_name in downloaded:
            continue
        print('Downloading', university_name)

        os.makedirs(university_name, exist_ok=True)
        urls = urls['urls']
        for url in urls:
            command = f"{base_command} -P {university_name} {url}"
            subprocess.run(command, shell=True)

        command2 = f'mv {university_name} /Volumes/External/system_data/suny/'
        subprocess.run(command2, shell=True)
        
        with open('data/downloaded.txt', 'a') as f:
            f.write(f"{university_name}\n")


if __name__ == "__main__":
    main()
