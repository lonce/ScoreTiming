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
    
    global_time = 0.0  # Global time in seconds
    measure_number = 0
    
    output = []
    events = []

    # Initialize the next timestamp time
    next_output_time = 0.0

    # Load all events from all tracks, calculating their absolute time
    for track in mid.tracks:
        absolute_time = 0
        for msg in track:
            absolute_time += msg.time
            events.append((absolute_time, msg))

    # Sort events by their absolute time across all tracks
    events.sort(key=lambda event: event[0])

    last_global_time = 0
    for event_time, msg in events:
        # Calculate the time delta from the last event time
        delta_ticks = event_time - last_global_time
        last_global_time = event_time

        # Update global time based on this event's time delta
        global_time += time_in_seconds(delta_ticks, tempo, ticks_per_beat)

        if msg.is_meta:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                print(f"Tempo change: {tempo} microseconds per beat ({60000000 / (tempo / 1_000_000)} BPM)")
            elif msg.type == 'time_signature':
                time_signature = (msg.numerator, msg.denominator)
                print(f"Time signature change: {msg.numerator}/{msg.denominator}")

        # Generate timestamps at exact intervals
        while global_time >= next_output_time:
            # Calculate the ticks corresponding to the next_output_time
            ticks_at_output_time = ticks_from_time(next_output_time, tempo, ticks_per_beat)
            
            # Calculate the measure and beat
            beats_per_measure = time_signature[0]
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
            next_output_time += 1.0 / timestamps_per_second

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
