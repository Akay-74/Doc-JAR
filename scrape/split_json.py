
import json
import os
import re

def split_json(input_file, output_dir, name_key):
    """
    Splits a JSON file containing a list of objects into individual
    JSON files for each object.

    Args:
        input_file (str): The path to the input JSON file.
        output_dir (str): The directory to save the individual JSON files.
        name_key (str): The key in each JSON object to use for the filename.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_file, 'r') as f:
        data = json.load(f)

    for item in data:
        # Create a valid filename from the name key
        filename = re.sub(r'[^a-zA-Z0-9_]', '_', item[name_key]) + '.json'
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(item, f, indent=2)

if __name__ == '__main__':
    split_json('diseases_dataset.json', 'diseases', 'disease_id')
    split_json('lab_reference_ranges.json', 'lab_tests', 'test_name')
    split_json('medications_dataset.json', 'medications', 'drug_id')
