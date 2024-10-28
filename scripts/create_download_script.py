"""
Script to create the bash script to download SUNY schools from the metadata file


download_site https://www.sunysuffolk.edu/_resources/webservice/output/catalog/catalog-master-final-web.html
"""
import os
import json
import subprocess

from src.constants import UNIVERSITY_DATA_DIR, MAX_DOWNLOAD_THREADS, METADATA_PATH

opj = os.path.join

base_command = f'wget2 --reject jpg,jpeg,png,gif,css,js,woff,woff2,svg --mirror --convert-links --adjust-extension --force-directories --page-requisites --no-parent --user-agent=Mozilla/5.0 --max-threads {MAX_DOWNLOAD_THREADS} '


def main():

    with open(METADATA_PATH, 'r') as f:
        data = json.load(f)

    with open(opj('scripts', 'download_suny.sh'), 'w') as cf:

        for university_name, urls in data.items():
            urls = urls['urls']
            for url in urls:
                command = f"{base_command} -P {university_name} {url}"
                cf.write(command + '\n')

            command2 = f'mv {university_name} {UNIVERSITY_DATA_DIR}'
            cf.write(command2 + '\n')


if __name__ == "__main__":
    main()
