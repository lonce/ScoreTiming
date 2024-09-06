import mido
import math
import argparse

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.midiscoretools import update_json_metadata

def sine_wave(period, amplitude, tick):
    frequency = 2 * math.pi / period
    sine_value = math.sin(frequency * tick)
    return 2 ** (sine_value * amplitude)

def find_true_end_tick(midi_file):
    end_tick = 0
    for track in midi_file.tracks:
        track_ticks = sum(msg.time for msg in track)
        end_tick = max(end_tick, track_ticks)
    return end_tick

def process_midi_file(input_file, period, amplitude, spacing):
    mid = mido.MidiFile(input_file)
    output_mid = mido.MidiFile(type=mid.type, ticks_per_beat=mid.ticks_per_beat)

    tempo_track = mido.MidiTrack()
    output_mid.tracks.append(tempo_track)

    current_tempo = 500000  # Default tempo (120 BPM)
    last_tempo_change_tick = 0
    cumulative_tick = 0
    
    # Find the true end tick of the original file
    true_end_tick = find_true_end_tick(mid)

    # First pass: collect all tempo changes
    tempo_changes = []
    for msg in mid.tracks[0]:
        cumulative_tick += msg.time
        if msg.type == 'set_tempo':
            tempo_changes.append((cumulative_tick, msg.tempo))
    
    if tempo_changes:
        current_tempo = tempo_changes[0][1]  # Use the first tempo if available

    cumulative_tick = 0
    last_original_tempo_index = -1

    # Second pass: process tempo track
    for msg in mid.tracks[0]:
        delta_ticks = msg.time
        cumulative_tick += delta_ticks

        # Add new tempo events at specified intervals, update the following event delta ticks
        while last_tempo_change_tick + spacing <= cumulative_tick:
            new_tempo_tick = last_tempo_change_tick + spacing
            factor = sine_wave(period, amplitude, new_tempo_tick)
            
            # Find the current original tempo
            while last_original_tempo_index + 1 < len(tempo_changes) and tempo_changes[last_original_tempo_index + 1][0] <= new_tempo_tick:
                last_original_tempo_index += 1
            original_tempo = tempo_changes[last_original_tempo_index][1] if last_original_tempo_index >= 0 else current_tempo
            
            new_tempo = int(original_tempo / factor)
            new_delta_ticks = new_tempo_tick - last_tempo_change_tick
            
            new_tempo_msg = mido.MetaMessage('set_tempo', tempo=new_tempo, time=new_delta_ticks)
            tempo_track.append(new_tempo_msg)
            
            last_tempo_change_tick = new_tempo_tick

        # Adjust the delta ticks of the original message
        adjusted_delta_ticks = cumulative_tick - last_tempo_change_tick
        
        if msg.type == 'set_tempo':
            factor = sine_wave(period, amplitude, cumulative_tick)
            new_tempo = int(msg.tempo / factor)
            new_msg = mido.MetaMessage('set_tempo', tempo=new_tempo, time=adjusted_delta_ticks)
        else:
            new_msg = msg.copy(time=adjusted_delta_ticks)
        
        tempo_track.append(new_msg)
        last_tempo_change_tick = cumulative_tick

    # Ensure the tempo track extends to the true end of the file
    if cumulative_tick < true_end_tick:
        remaining_ticks = true_end_tick - cumulative_tick
        tempo_track.append(mido.MetaMessage('text', text='File end padding', time=remaining_ticks))

    # Process other tracks (no changes necessary since delta ticks don't change with BPM!)
    for track in mid.tracks[1:]:
        new_track = mido.MidiTrack()
        output_mid.tracks.append(new_track)
        for msg in track:
            new_track.append(msg.copy())

    # Add end of track message to all tracks
    for track in output_mid.tracks:
        if not track or track[-1].type != 'end_of_track':
            end_of_track = mido.MetaMessage('end_of_track', time=0)
            track.append(end_of_track)

    return output_mid


def main():
    parser = argparse.ArgumentParser(description="Vary tempo of a MIDI file using a sine wave")
    parser.add_argument("-m", "--midi", required=True, help="Input MIDI file")
    parser.add_argument("-om", "--output", required=True, help="Output MIDI file")
    parser.add_argument("-p", "--period", type=int, required=True, help="Sine wave period in ticks")
    parser.add_argument("-a", "--amplitude", type=float, required=True, help="Sine wave amplitude in octaves")
    parser.add_argument("-sp", "--spacing", type=int, required=True, help="Spacing between new tempo events in ticks")
    parser.add_argument("-j", "--metadata", nargs="?", default=None, help="Path to the variation metadata json")
    
    args = parser.parse_args()

    output_mid=process_midi_file(args.midi, args.period, args.amplitude, args.spacing)
    print(f"Processed MIDI file saved as {args.output}")



    output_mid.save(args.output)

    if (args.metadata != None) : 
        update_json_metadata(args.metadata, {
            "Variator program" : f'tempoVariator_ticks (sine) --period {args.period} --amplitude {args.amplitude} --spacing {args.spacing}'),
        })


if __name__ == "__main__":
    main()