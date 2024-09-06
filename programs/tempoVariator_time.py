import mido
import math
import argparse

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.midiscoretools import update_json_metadata

def sine_wave(period, amplitude, time):
    """
    A sin wave interpreted as units in octaves (eg,  sin[-1,1] maps to [.5, 2].
    """
    frequency = 2 * math.pi / period
    sine_value = math.sin(frequency * time)
    return 2 ** (sine_value * amplitude)

def find_last_event_tick(midi_file):
    return max(sum(msg.time for msg in track) for track in midi_file.tracks)

def process_midi_file(input_file, period, amplitude, spacing):
    mid = mido.MidiFile(input_file)
    output_mid = mido.MidiFile(type=mid.type, ticks_per_beat=mid.ticks_per_beat)

    last_event_tick = find_last_event_tick(mid)

    tempo_track = mido.MidiTrack()
    output_mid.tracks.append(tempo_track)

    current_tempo = 500000  # Default tempo (120 BPM)
    last_tempo_change_tick = 0
    cumulative_tick = 0
    cumulative_time = 0.0
    next_sample_time = spacing

    # Collect all original tempo changes
    tempo_changes = []
    for msg in mid.tracks[0]:
        cumulative_tick += msg.time
        if msg.type == 'set_tempo':
            tempo_changes.append((cumulative_tick, msg.tempo))
            current_tempo = msg.tempo

    cumulative_tick = 0
    last_original_tempo_index = -1

    # Process tempo track (track 0)
    for msg in mid.tracks[0]:
        delta_ticks = msg.time
        cumulative_tick += delta_ticks
        delta_time = mido.tick2second(delta_ticks, mid.ticks_per_beat, current_tempo)
        cumulative_time += delta_time

        while cumulative_time >= next_sample_time and cumulative_tick < last_event_tick:
            # Calculate ticks to the next sample point
            ticks_to_next_sample = mido.second2tick(next_sample_time - (cumulative_time - delta_time), mid.ticks_per_beat, current_tempo)
            
            if ticks_to_next_sample > 0 and ticks_to_next_sample < delta_ticks:
                factor = sine_wave(period, amplitude, next_sample_time)
                
                # Find the current original tempo
                while last_original_tempo_index + 1 < len(tempo_changes) and tempo_changes[last_original_tempo_index + 1][0] <= cumulative_tick:
                    last_original_tempo_index += 1
                original_tempo = tempo_changes[last_original_tempo_index][1] if last_original_tempo_index >= 0 else current_tempo
                
                new_tempo = int(original_tempo / factor)
                
                # Insert new tempo change
                new_tempo_msg = mido.MetaMessage('set_tempo', tempo=new_tempo, time=ticks_to_next_sample)
                tempo_track.append(new_tempo_msg)
                
                # Adjust remaining ticks for the current message
                delta_ticks -= ticks_to_next_sample
                current_tempo = new_tempo

            next_sample_time += spacing

        # Add the original message (or its remainder) with adjusted time
        if msg.type == 'set_tempo':
            factor = sine_wave(period, amplitude, cumulative_time)
            new_tempo = int(msg.tempo / factor)
            new_msg = mido.MetaMessage('set_tempo', tempo=new_tempo, time=delta_ticks)
            current_tempo = new_tempo
        else:
            new_msg = msg.copy(time=delta_ticks)
        
        if delta_ticks > 0:
            tempo_track.append(new_msg)

    # Process other tracks (copy as is)
    for track in mid.tracks[1:]:
        new_track = mido.MidiTrack()
        output_mid.tracks.append(new_track)
        for msg in track:
            new_track.append(msg.copy())

    # Ensure all tracks end with end_of_track message
    for track in output_mid.tracks:
        if track[-1].type != 'end_of_track':
            track.append(mido.MetaMessage('end_of_track', time=0))

    return output_mid
    

def main():
    parser = argparse.ArgumentParser(description="Vary tempo of a MIDI file using a sine wave")
    parser.add_argument("-m", "--midi", required=True, help="Input MIDI file")
    parser.add_argument("-om", "--output", required=True, help="Output MIDI file")
    parser.add_argument("-p", "--period", type=float, required=True, help="Sine wave period in seconds")
    parser.add_argument("-a", "--amplitude", type=float, required=True, help="Sine wave amplitude in octaves")
    parser.add_argument("-sp", "--spacing", type=float, required=True, help="Spacing between new tempo events in seconds")
    parser.add_argument("-j", "--metadata", nargs="?", default=None, help="Path to the variation metadata json")
    
    args = parser.parse_args()

    output_mid=process_midi_file(args.midi, args.period, args.amplitude, args.spacing)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    output_mid.save(args.output)


    if (args.metadata != None) : 
        update_json_metadata(args.metadata, {
            "Variator program" : f'tempoVariator_time (sine) --period {args.period} --amplitude {args.amplitude} --spacing {args.spacing}',
        })


    print(f"Processed MIDI file saved as {args.output}")

if __name__ == "__main__":
    main()