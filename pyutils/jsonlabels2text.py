import json
import sys
import os

def process_json_file(input_file):
    # Check if the input file exists
    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' not found.")
        return
    
    # Read the JSON data from the file
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Extract the "time-positions" attribute
    time_positions = data.get("time-positions", [])

    # Prepare the output file name by changing the extension to .txt
    output_file = os.path.splitext(input_file)[0] + '.txt'

    # Write the formatted data to the output file
    with open(output_file, 'w') as f:
        for triplet in time_positions:
            if len(triplet) == 3:
                time, bar_number, beat_number = triplet
                f.write(f"{time}\t{time}\t{bar_number},{beat_number}\n")
            else:
                print(f"Warning: Invalid triplet found in the data: {triplet}")

    print(f"Output written to: {output_file}")

if __name__ == "__main__":
    # Check if the input file name is provided as an argument
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_file.jsn>")
    else:
        input_file = sys.argv[1]
        process_json_file(input_file)
