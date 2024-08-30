import mido
import argparse
from typing import Any

def format_midi_message(track_num: int, delta_ticks: int, total_ticks: int, msg: Any, current_time: float) -> str:
    """Format a MIDI message as a human-readable string with track number and delta ticks."""
    if isinstance(msg, mido.MetaMessage):
        return f"T {track_num} - Delta {delta_ticks} - total ({total_ticks}) - {current_time:.3f} - Meta: {msg.type}, {', '.join(f'{k}={v}' for k, v in msg.dict().items() if k not in ['type', 'time'])}"
    elif isinstance(msg, mido.Message):
        return f"T {track_num} - Delta {delta_ticks} - total ({total_ticks}) -{current_time:.3f} - {msg.type.capitalize()}: {', '.join(f'{k}={v}' for k, v in msg.dict().items() if k not in ['type', 'time'])}"
    else:
        return f"T {track_num} - Delta {delta_ticks} - total ({total_ticks}) -{current_time:.3f} - Unknown message type: {type(msg)}"

def parse_midi_file(file_path: str):
    """Parse the MIDI file and print human-readable messages with track numbers and delta ticks."""
    try:
        mid = mido.MidiFile(file_path)
        ticks_per_beat = mid.ticks_per_beat
        print(f"MIDI File: {file_path}")
        print(f"Type: {mid.type}")
        print(f"Ticks per beat (PPQ): {ticks_per_beat}")
        print("\nMessages:")

        total_ticks_per_track = []

        # Initial tempo is 500000 microseconds per beat (120 BPM)
        tempo = 500000
        ticks_per_second = ticks_per_beat * (1_000_000 / tempo)

        for i, track in enumerate(mid.tracks):
            current_time = 0
            total_ticks = 0
            for msg in track:
                delta_ticks = msg.time
                total_ticks += delta_ticks
                if msg.is_meta and msg.type == 'set_tempo':
                    tempo = msg.tempo
                    ticks_per_second = ticks_per_beat * (1_000_000 / tempo)
                
                # Calculate time in seconds based on the current tempo
                current_time += delta_ticks * (tempo / 1_000_000) / ticks_per_beat

                print(format_midi_message(i + 1, delta_ticks, total_ticks, msg, current_time))
            
            total_ticks_per_track.append(total_ticks)

        # Print the total delta ticks for each track
        print("\nTotal Delta Ticks per Track:")
        for i, total_ticks in enumerate(total_ticks_per_track):
            print(f"Track {i + 1}: {total_ticks} ticks")

    except Exception as e:
        print(f"An error occurred while parsing the MIDI file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Parse a MIDI file and output human-readable messages.")
    parser.add_argument("-f", "--file", required=True, help="Input MIDI file path")
    args = parser.parse_args()

    parse_midi_file(args.file)

if __name__ == "__main__":
    main()
