import argparse
import mido
import math

def is_compound_time(numerator, denominator):
    return numerator % 3 == 0 and numerator > 3 and denominator >= 8

def beats_per_measure(numerator, denominator):
    if is_compound_time(numerator, denominator):
        return numerator // 3
    return numerator

def process_midi(midi_file, frame_rate, output_file):
    mid = mido.MidiFile(midi_file)
    
    tempo = 500000  # Default tempo (microseconds per beat)
    tempo_changes = [(0, tempo)]
    time_sig_changes = [(0, (4, 4))]  # Default 4/4 time signature
    
    total_ticks = 0
    for track in mid.tracks:
        track_tick = 0
        for msg in track:
            track_tick += msg.time
            total_ticks = max(total_ticks, track_tick)
            if msg.type == 'set_tempo':
                tempo_changes.append((track_tick, msg.tempo))
            elif msg.type == 'time_signature':
                time_sig_changes.append((track_tick, (msg.numerator, msg.denominator)))
    
    tempo_changes.sort(key=lambda x: x[0])
    time_sig_changes.sort(key=lambda x: x[0])
    
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
    total_beats = total_ticks / mid.ticks_per_beat  # Corrected beat calculation
    
    print(f"PPQ (ticks per beat): {mid.ticks_per_beat}")
    print(f"Total number of beats: {total_beats:.2f}")
    print(f"Total number of ticks: {total_ticks}")
    
    print("\nTime Signature Changes:")
    for tick, (numerator, denominator) in time_sig_changes:
        beats = beats_per_measure(numerator, denominator)
        print(f"Tick {tick}: Time signature changed to {numerator}/{denominator} ({beats} beats per measure)")
    
    with open(output_file, 'w') as out:
        frame_duration = 1 / frame_rate
        num_frames = math.ceil(total_time * frame_rate)
        
        for frame in range(num_frames):
            frame_center_time = (frame + 0.5) * frame_duration
            
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