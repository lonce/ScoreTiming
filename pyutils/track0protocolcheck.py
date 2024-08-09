import mido
import argparse

def check_first_track_protocol(midi_file_path):
    midi = mido.MidiFile(midi_file_path)
    
    # Check if the MIDI file is type 1
    if midi.type != 1:
        return (False, "MIDI file is not of type 1.")

    first_track = midi.tracks[0]
    
    # Check for presence of global metadata events
    has_tempo = False
    has_time_signature = False
    has_key_signature = False
    has_non_musical_events = False

    for msg in first_track:
        if msg.type == 'set_tempo':
            has_tempo = True
        elif msg.type == 'time_signature':
            has_time_signature = True
        elif msg.type == 'key_signature':
            has_key_signature = True
        elif msg.type in ['track_name', 'marker', 'text', 'copyright']:
            has_non_musical_events = True
        elif msg.type in ['note_on', 'note_off']:
            return (False, "First track contains musical note events.")

    reasons = []
    if not has_tempo:
        reasons.append("missing tempo event")
    if not has_time_signature:
        reasons.append("missing time signature event")
    if not (has_key_signature or has_non_musical_events):
        reasons.append("missing key signature or non-musical events (e.g., track name, marker)")

    if reasons:
        first_track_protocol_result = (False, "First track does not contain all necessary global metadata events: " + ", ".join(reasons) + ".")
    else:
        first_track_protocol_result = (True, "First track satisfies the protocol.")
    
    return first_track_protocol_result

def check_other_tracks(midi_file_path):
    midi = mido.MidiFile(midi_file_path)

    other_tracks_metadata_events = {
        "tempo": [],
        "time_signature": [],
        "key_signature": []
    }

    for i, track in enumerate(midi.tracks[1:], start=1):
        for msg in track:
            if msg.type == 'set_tempo':
                other_tracks_metadata_events["tempo"].append((i, msg))
            elif msg.type == 'time_signature':
                other_tracks_metadata_events["time_signature"].append((i, msg))
            elif msg.type == 'key_signature':
                other_tracks_metadata_events["key_signature"].append((i, msg))
    
    other_tracks_result = []
    for event_type, events in other_tracks_metadata_events.items():
        if events:
            other_tracks_result.append(f"Found {event_type.replace('_', ' ')} events in other tracks: {[(track_num, str(msg)) for track_num, msg in events]}")
    
    if not other_tracks_result:
        return "No tempo, time signature, or key signature events found in tracks other than the first one."
    else:
        return "\n".join(other_tracks_result)

def main():
    parser = argparse.ArgumentParser(description="Check if the first track of a MIDI file satisfies the typical protocol for a type 1 MIDI file and identify metadata events in other tracks.")
    parser.add_argument('-im', '--input_midi', type=str, required=True, help="Path to the input MIDI file")
    args = parser.parse_args()

    first_track_result = check_first_track_protocol(args.input_midi)
    other_tracks_message = check_other_tracks(args.input_midi)

    print(first_track_result[1])
    print(other_tracks_message)

if __name__ == "__main__":
    main()
