import struct
import sys

def read_midi_header(file_path):
    with open(file_path, 'rb') as f:
        # Read the first 14 bytes (Header Chunk is 14 bytes long)
        header = f.read(14)
        
        # Verify the start of the header chunk (should be "MThd")
        chunk_type, header_length, format_type, num_tracks, division = struct.unpack('>4sLHHH', header)
        
        if chunk_type != b'MThd':
            raise ValueError("This does not appear to be a valid MIDI file.")
        
        print(f"Chunk Type: {chunk_type.decode('ascii')}")
        print(f"Header Length: {header_length} bytes")
        print(f"Format Type: {format_type}")
        print(f"Number of Tracks: {num_tracks}")
        
        if division & 0x8000 == 0:
            # This is a PPQ format
            ppq = division & 0x7FFF
            print(f"Division: {ppq} ticks per quarter note (PPQ)")
        else:
            # This is SMPTE format
            frames_per_second = -(division >> 8)
            ticks_per_frame = division & 0xFF
            print(f"Division: {frames_per_second} frames per second, {ticks_per_frame} ticks per frame (SMPTE)")
        
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python read_midi_header.py <midi_file_path>")
        sys.exit(1)
    
    midi_file_path = sys.argv[1]
    try:
        read_midi_header(midi_file_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
