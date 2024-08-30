import mido
import argparse
from bisect import bisect_right

def read_input_times(file_path):
    with open(file_path, 'r') as f:
        return [tuple(float(x) if i < 2 else x for i, x in enumerate(line.strip().split('\t'))) for line in f]

def write_output_times(file_path, mapped_times):
    with open(file_path, 'w') as f:
        for start, end, label in mapped_times:
            f.write(f"{start:.6f}\t{end:.6f}\t{label}\n")

def compute_time_array(midi_file):
    mid = mido.MidiFile(midi_file)
    ticks_total = sum(msg.time for msg in mid.tracks[0])
    time_array = [0.0] * (ticks_total + 1)
    
    current_tempo = 500000  # Default tempo (120 BPM)
    current_tick = 0
    current_time = 0.0
    
    for msg in mid.tracks[0]:
        for tick in range(current_tick, current_tick + msg.time):
            time_array[tick] = current_time
        
        delta_time = mido.tick2second(msg.time, mid.ticks_per_beat, current_tempo)
        current_time += delta_time
        current_tick += msg.time
        
        if msg.type == 'set_tempo':
            current_tempo = msg.tempo
    
    time_array[-1] = current_time  # Set the last element to the total duration
    return time_array, ticks_total

def map_time(time, source_array, target_array):
    if time == 0:
        return 0
    index = bisect_right(source_array, time) - 1
    source_time1, source_time2 = source_array[index], source_array[index + 1]
    target_time1, target_time2 = target_array[index], target_array[index + 1]
    
    # Linear interpolation
    ratio = (time - source_time1) / (source_time2 - source_time1)
    return target_time1 + ratio * (target_time2 - target_time1)

def map_times(midi_file1, midi_file2, input_times_file, output_times_file):
    a1, ticks1 = compute_time_array(midi_file1)
    a2, ticks2 = compute_time_array(midi_file2)
    
    if ticks1 != ticks2:
        raise ValueError(f"The two MIDI files have different numbers of ticks: {ticks1} vs {ticks2}")
    
    input_events = read_input_times(input_times_file)
    mapped_events = []
    
    for start, end, label in input_events:
        new_start = map_time(start, a1, a2)
        new_end = map_time(end, a1, a2)
        mapped_events.append((new_start, new_end, label))
    
    write_output_times(output_times_file, mapped_events)

def main():
    parser = argparse.ArgumentParser(description="Map times between two MIDI files")
    parser.add_argument("-m1", required=True, help="First input MIDI file")
    parser.add_argument("-m2", required=True, help="Second input MIDI file")
    parser.add_argument("-it", required=True, help="Input time file")
    parser.add_argument("-ot", required=True, help="Output time file")
    
    args = parser.parse_args()

    try:
        map_times(args.m1, args.m2, args.it, args.ot)
        print(f"Mapped times saved as {args.ot}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()