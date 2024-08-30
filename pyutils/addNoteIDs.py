import xml.etree.ElementTree as ET
import argparse

def add_note_ids(input_file, output_file):
    # Parse the XML file
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Find all note elements
    notes = root.findall('.//note')

    # Add unique ID to each note
    for i, note in enumerate(notes, start=1):
        note.set('id', f'n{i}')

    # Write the modified XML to the output file
    tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    print(f"Modified MusicXML file written to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Add unique IDs to notes in a MusicXML file.")
    parser.add_argument("input_file", help="Path to the input MusicXML file")
    parser.add_argument("output_file", help="Path to the output MusicXML file")
    args = parser.parse_args()

    add_note_ids(args.input_file, args.output_file)

if __name__ == "__main__":
    main()
    