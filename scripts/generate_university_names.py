import json


def main():
    """Main program."""

    with open('data/metadata.json', 'r') as json_file:
        metadata = json.load(json_file)

    with open('data/university_names.txt', 'w') as names_file:
        for name in metadata:
            # TODO: do we need to remove hyphens somehow???
            names_file.write(name + '\n')


if __name__ == '__main__':
    main()
