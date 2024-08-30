import argparse
import mido
import math

def process_midi(midi_file, frame_rate, output_file):
    mid = mido.MidiFile(midi_file)
    
    tempo = 500000  # Default tempo (microseconds per beat)
    tempo_changes = [(0, tempo)]
    
    # First pass: collect all tempo changes and calculate total ticks
    total_ticks = 0
    for track in mid.tracks:
        track_tick = 0
        for msg in track:
            track_tick += msg.time
            total_ticks = max(total_ticks, track_tick)
            if msg.type == 'set_tempo':
                tempo_changes.append((track_tick, msg.tempo))
    
    tempo_changes.sort(key=lambda x: x[0])
    
    def tick_to_time(tick):
        nonlocal tempo
        time = 0
        last_tempo_tick = 0
        for tempo_tick, new_tempo in tempo_changes:
            if tempo_tick >= tick:
                break
            time += (tempo_tick - last_tempo_tick) * tempo / (mid.ticks_per_beat * 1000000)
            last_tempo_tick = tempo_tick
            tempo = new_tempo
        time += (tick - last_tempo_tick) * tempo / (mid.ticks_per_beat * 1000000)
        return time
    
    total_time = tick_to_time(total_ticks)
    
    # Print requested information to console
    print(f"PPQ (ticks per beat): {mid.ticks_per_beat}")
    print(f"Total number of beats: {total_ticks / mid.ticks_per_beat:.2f}")
    print(f"Total number of ticks: {total_ticks}")
    
    with open(output_file, 'w') as out:
        frame_duration = 1 / frame_rate
        num_frames = math.ceil(total_time * frame_rate)
        
        for frame in range(num_frames):
            frame_center_time = (frame + 0.5) * frame_duration
            
            # Binary search to find the nearest tick
            left, right = 0, total_ticks
            while left < right:
                mid_tick = (left + right) // 2
                mid_time = tick_to_time(mid_tick)
                if mid_time < frame_center_time:
                    left = mid_tick + 1
                else:
                    right = mid_tick
            nearest_tick = left
            
            out.write(f"{frame},{frame_center_time:.6f},{nearest_tick}\n")

def main():
    parser = argparse.ArgumentParser(description="Process MIDI file and output frame-tick information")
    parser.add_argument("midi_file", help="Path to the MIDI file")
    parser.add_argument("frame_rate", type=float, help="Frame rate in frames per second")
    parser.add_argument("output_file", help="Path to the output text file")
    args = parser.parse_args()
    
    process_midi(args.midi_file, args.frame_rate, args.output_file)

if __name__ == "__main__":
    main()