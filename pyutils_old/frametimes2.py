import mido
import argparse

def time_in_seconds(ticks, tempo, ticks_per_beat):
    """Convert delta ticks to time in seconds given the current tempo and ticks per beat."""
    return (ticks * tempo) / (ticks_per_beat * 1_000_000)

def ticks_from_time(time_seconds, tempo, ticks_per_beat):
    """Convert time in seconds to delta ticks given the current tempo and ticks per beat."""
    return int(time_seconds * ticks_per_beat * 1_000_000 / tempo)

def process_midi_file(midi_file, timestamps_per_second, output_file):
    mid = mido.MidiFile(midi_file)
    
    ticks_per_beat = mid.ticks_per_beat
    print(f"Ticks per beat: {ticks_per_beat}")
    
    tempo = 500000  # Default tempo (500000 microseconds per beat, equivalent to 120 BPM)
    time_signature = (4, 4)  # Default time signature is 4/4
    
    current_time = 0.0  # Time in seconds
    measure_number = 0
    
    output = []
    ticks_in_current_measure = 0
    beats_per_measure = time_signature[0]  # Initially set to 4

    # Calculate the time interval based on the timestamps per second
    output_interval = 1.0 / timestamps_per_second

    # Initialize the next timestamp time
    next_output_time = 0.0

    # Initialize tick count
    tick_count = 0

    # Iterate through the MIDI file to extract timing information
    for track in mid.tracks:
        for msg in track:
            if msg.is_meta:
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                    print(f"Tempo change: {tempo} microseconds per beat ({60000000 / (tempo / 1_000_000)} BPM)")
                elif msg.type == 'time_signature':
                    time_signature = (msg.numerator, msg.denominator)
                    beats_per_measure = time_signature[0]
                    print(f"Time signature change: {msg.numerator}/{msg.denominator}")

            tick_count += msg.time
            current_time += time_in_seconds(msg.time, tempo, ticks_per_beat)
            
            # Generate timestamps at exact intervals
            while current_time >= next_output_time:
                # Calculate the ticks corresponding to the next_output_time
                ticks_at_output_time = ticks_from_time(next_output_time, tempo, ticks_per_beat)
                
                # Calculate the measure and beat
                ticks_in_current_measure = ticks_at_output_time % (beats_per_measure * ticks_per_beat)
                beat_number = 1 + (ticks_in_current_measure // ticks_per_beat)
                
                # Handle new measure
                if ticks_in_current_measure == 0 and next_output_time != 0:
                    measure_number += 1

                # Floating point beat number
                beat_number_float = beat_number + (ticks_in_current_measure % ticks_per_beat) / ticks_per_beat
                
                # Add the result to the output list
                output.append((next_output_time, ticks_at_output_time, measure_number, beat_number_float))

                # Move to the next output time
                next_output_time += output_interval

    # Write the output to the specified output file
    with open(output_file, 'w') as f:
        for entry in output:
            f.write(f"{entry[0]:.6f}\t{entry[1]}\t{entry[2]}\t{entry[3]:.6f}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract timing information from a MIDI file.')
    parser.add_argument('-m', '--midifile', required=True, help='The MIDI file to process.')
    parser.add_argument('-r', '--rate', required=True, type=float, help='The rate of time stamps per second (can be a float).')
    parser.add_argument('-o', '--output', required=True, help='The output text file to write results to.')

    args = parser.parse_args()

    process_midi_file(args.midifile, args.rate, args.output)
    print(f"Output written to '{args.output}'")
