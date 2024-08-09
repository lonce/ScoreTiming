import mido
import argparse
from typing import Any

def format_midi_message(msg: Any, current_time: float) -> str:
    """Format a MIDI message as a human-readable string."""
    if isinstance(msg, mido.MetaMessage):
        return f"{current_time:.3f} - Meta: {msg.type}, {', '.join(f'{k}={v}' for k, v in msg.dict().items() if k not in ['type', 'time'])}"
    elif isinstance(msg, mido.Message):
        return f"{current_time:.3f} - {msg.type.capitalize()}: {', '.join(f'{k}={v}' for k, v in msg.dict().items() if k not in ['type', 'time'])}"
    else:
        return f"{current_time:.3f} - Unknown message type: {type(msg)}"

def parse_midi_file(file_path: str):
    """Parse the MIDI file and print human-readable messages."""
    try:
        mid = mido.MidiFile(file_path)
        print(f"MIDI File: {file_path}")
        print(f"Type: {mid.type}")
        print(f"Ticks per beat: {mid.ticks_per_beat}")
        print("\nMessages:")
        
        current_time = 0
        for msg in mid:
            current_time += msg.time
            print(format_midi_message(msg, current_time))
    except Exception as e:
        print(f"An error occurred while parsing the MIDI file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Parse a MIDI file and output human-readable messages.")
    parser.add_argument("-f", "--file", required=True, help="Input MIDI file path")
    args = parser.parse_args()

    parse_midi_file(args.file)

if __name__ == "__main__":
    main()