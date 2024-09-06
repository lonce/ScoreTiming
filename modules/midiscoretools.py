# module midiscoretools.py

from music21 import midi, meter, tempo, converter
import os 
import json
from datetime import datetime
from music21.midi import MidiFile, MetaEvents, getNumber, ChannelVoiceMessages

from collections import namedtuple
import bisect
import struct
from music21.midi.translate import getTimeForEvents

import numpy as np
from scipy import sparse

import subprocess


def create_json_file_if_not_exists(file_name):
    # Ensure the directory exists
    directory = os.path.dirname(file_name)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # Create the file with an empty JSON object if it doesn't exist
    if not os.path.exists(file_name):
        with open(file_name, 'w') as f:
            json.dump({}, f)
        print(f"File created with empty JSON object: {file_name}")


def update_json_metadata(file_name, new_data):
    """
    Reads the existing JSON data from a file, merges it with new data, adds a timestamp,
    and writes it back to the file.

    Parameters:
    file_name (str): The path to the JSON file.
    new_data (dict): The new JSON data to be merged with the existing data.
    """
    # Step 1: Read the existing file if it exists, else start with an empty dictionary
    create_json_file_if_not_exists(file_name)
    with open(file_name, 'r') as f:
            data = json.load(f)

    # if os.path.exists(file_name):
    #     with open(file_name, 'r') as f:
    #         data = json.load(f)
    # else:
    #     data = {}

    # Step 2: Add the current date and time
    current_datetime = datetime.now().isoformat()  # ISO 8601 format
    new_data['date_written'] = current_datetime

    # Step 3: Update the existing data with new data (merge the dictionaries)
    data.update(new_data)

    # Step 4: Write the merged data back to the file (overwrite or create if necessary)
    with open(file_name, 'w') as f:
        json.dump(data, f, indent=4)




# I think recent python versions may have this built-in
def float_range(start, stop, step):
    while start < stop:
        yield round(start, 10)  # rounding to avoid floating-point precision issues
        start += step
        

#This is handy because we use both scipy's compression for sparse matrices and np's savez  and they are inconstent about generating and using the extension
def addExtensionIfNeeded(fname, ext="npz") :
    # Split the filename into name and extension
    name_parts = fname.split('.')
     
    # Check if the last part is ext (case insensitive)
    fnameext=name_parts[-1].lower()
    if (fnameext) != ext:
        # If not, add ext as a new extension
        fname = fname + '.'+ext
    return fname



def render_wav_with_fluidsynth(midi_file,  output_wav_file):
    command = [
        "fluidsynth",
        "-ni",              # No interactive mode
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",     # Path to the SoundFont file (.sf2)
        midi_file,          # Path to the MIDI file
        "-F", output_wav_file,  # Output to WAV file
        "-r", "44100"       # Sample rate (optional, 44100 Hz in this example)
    ]

    subprocess.run(command, check=True)

    

def loadBitmap(fname) :
    # To load the sparse matrix:
    fname=addExtensionIfNeeded(fname, 'npz')
    loaded_sparse_matrix = sparse.load_npz(fname)

    # Convert the sparse matrix back to a dense numpy array:
    return loaded_sparse_matrix.toarray()

def saveBitmap(fname, m) :
    sparse_matrix = sparse.csr_matrix(m)
    fname=addExtensionIfNeeded(fname, 'npz')
    sparse.save_npz(fname , sparse_matrix, compressed=True)


#################################################################################
# Used to convert midi file to a bit map
#################################################################################
TempoEntry = namedtuple("TempoEntry", ("start_ticks", "start_ms", "microsecondsPerTick"))

def _read_midi_pitches_intervals(midi_file, **kwargs):
    midi = MidiFile()
    midi.open(midi_file)
    midi.read()


    # look for set_tempo in Track0
    track0 = midi.tracks[0]
    tempos = []

    for t, ev in getTimeForEvents(track0):
        if ev.type == MetaEvents.SET_TEMPO:

            #print(f' ev.data is  {ev.data}')
            #need to index a tuple in the notebook, but in the module getNumber is already an in
            #print(f' mspq will be set to {getNumber(ev.data, 3)}[0]')
            #print(f' mspq will be set to {getNumber(ev.data, 3)}')
            mspq = getNumber(ev.data, 3)  # first data is number
            #print(f' mspq is { mspq }')



            microsecondsPerTick = float(mspq) / midi.ticksPerQuarterNote
            if len(tempos) == 0:
                segment_start_ms = t * microsecondsPerTick
            else:
                segment_start_ms = tempos[-1].start_ms + (t - tempos[-1].start_ticks) * tempos[-1].microsecondsPerTick
            tempos.append(TempoEntry(t, segment_start_ms, microsecondsPerTick))

    midi.close()
    result = []

    if "midi_tracks" in kwargs:
        tracks = kwargs["midi_tracks"]
    else:
        tracks = range(len(midi.tracks))

    for track_index in tracks:
        #print(f'track_index = {track_index}')
        track = midi.tracks[track_index]
        raw_events = getTimeForEvents(track)
        events = {}
        for t, ev in raw_events:
            tempo = tempos[bisect.bisect_right(tempos, t, key=lambda x: x.start_ticks) - 1]
            seconds = (tempo.start_ms + (t - tempo.start_ticks) * tempo.microsecondsPerTick) / 1e6
            if ev.type == ChannelVoiceMessages.NOTE_ON and ev.velocity > 0:
                note_key = (ev.pitch, ev.channel)
                if not note_key in events:
                    events[note_key] = [(seconds, ev.velocity)]
                else:
                    events[note_key].append((seconds, ev.velocity))
            elif ev.type == ChannelVoiceMessages.NOTE_OFF or (ev.type == ChannelVoiceMessages.NOTE_ON and ev.velocity == 0):
                note_key = (ev.pitch, ev.channel)
                if note_key in events:
                    for time, velocity in events[note_key]:
                        if seconds > time:
                            result.append([time, seconds, ev.pitch])
                    del events[note_key]
    if len(result) > 0:
        result = sorted(result, key=lambda x: x[0])
        start, end, pitches = zip(*result)
        return np.array(pitches), np.array(list(zip(start, end)))
    else:
        return np.array([]), np.empty(shape=[0,2])


def midi_to_bitmap(file_name, fps = 86.1238):
    '''
    Converts a midi file to a bitmap of 128 rows (midi pitches) by seconds*fps 
        with a 0 or 1 in the frame/note space if a midi note is on there.
    '''
    hop=1/fps
    ext = os.path.splitext(file_name)[1].lower()[1:]
    pitches, intervals = _read_midi_pitches_intervals(file_name)
    # frames = np.zeros((int(np.max(intervals)/hop) + 1, max(pitches) + 1), dtype=int)
    frames = np.zeros((int(np.max(intervals)/hop) + 1, 128), dtype=int)
    print("frames.shape is {frames.shape}")
    for pitch, interval in zip(pitches, intervals):
        for i in range(int(interval[0] / hop), int(interval[1] / hop) + 1):
            frames[i][pitch] = 1
    return frames.swapaxes(1,0), min(pitches), max(pitches)


#################################################################################
# 
#################################################################################

def count_total_ticks(midi_file):
    '''
    Takes a midi_file file name
    RETURNS the number of ticks in the longest track (so the total duration of the piece in ticks)
    '''
    # Create a MidiFile instance and open the file
    mf = midi.MidiFile()
    mf.open(midi_file)
    
    # Read the MIDI file into memory
    mf.read()
    
    # Close the MIDI file as it's no longer needed
    mf.close()

    # Initialize a variable to store the maximum tick count
    total_ticks = 0
    
    # Iterate over all tracks to find the latest tick in each track
    for track in mf.tracks:
        current_ticks = 0
        for event in track.events:
            # Add the delta time of the current event to the running total
            current_ticks += event.time

        # After processing all events in the track, update the total_ticks
        total_ticks = max(total_ticks, current_ticks)

    return total_ticks



def extract_time_signatures(midi_file):
    '''
    Takes a midi file and returns a list of tuples consisting of 
    a tick number and a music21.meter.timeSignature:
    [(0, <music21.meter.TimeSignature 3/8>), ... (8880, <music21.meter.TimeSignature 6/8>)]
    '''
    mf = MidiFile()
    mf.open(midi_file)
    mf.read()

    time_signatures = []
    accumulated_ticks = 0
    
    for track in mf.tracks:
        accumulated_ticks = 0  # Reset for each track
        for event in track.events:
            if event.isDeltaTime:
                accumulated_ticks += event.time  # Accumulate delta time
            
            # Check for a time signature event
            if event.type == midi.MetaEvents.TIME_SIGNATURE:
                numerator = event.data[0]
                denominator = 2 ** event.data[1]  # The second byte is the denominator exponent
                time_signature_event = meter.TimeSignature(f"{numerator}/{denominator}")
                time_signatures.append((accumulated_ticks, time_signature_event))
    
    # Sort the time signatures by their tick position
    time_signatures.sort(key=lambda x: x[0])
    
    return time_signatures




###############################################################################################################
## ticks_per_beat_at_tick
## Ticks per beat can change not only with tempo messages, but with time signature messages, too. 
## 2/4 and 4/4 have one beat per quarter not, 3/8 and 6/8 have one beat per eigth note (and thus have the PPQ)
###############################################################################################################

def ticks_per_beat_at_tick(tick_value, time_signatures, ticks_per_quarter_note):
    '''
    ticks_per_beat_at_tick(tick_value, time_signatures, ticks_per_quarter_note)
        tick_value - the tick time at which you and to know the tpb
        time_signatures - a datasctructure you can create with extract_time_signatures(mf) 
        ticks_per_quarter_note - ttte PPQ (note: not always equal to tpb - eg 6/8 has PPQ/2 tpb!)
    '''
    current_time_signature = meter.TimeSignature('4/4')  # Default to 4/4 if no signature is found
    
    # Find the most recent time signature before the given tick_value
    for tick, time_sig in time_signatures:
        if tick <= tick_value:
            current_time_signature = time_sig
        else:
            break
    
    # Calculate the ticks per beat based on the current time signature
    denominator = current_time_signature.denominator
    if denominator == 4:
        ticks_per_beat = ticks_per_quarter_note  # quarter note gets a beat
    elif denominator == 8 and current_time_signature.numerator % 3 == 0:
        ticks_per_beat = ticks_per_quarter_note // 2  # eighth note gets a beat (e.g., 6/8 time)
    elif denominator == 8:
        ticks_per_beat = ticks_per_quarter_note // 2  # eighth note gets a beat
    else:
        ticks_per_beat = ticks_per_quarter_note // (denominator // 4)  # other time signatures
    
    return ticks_per_beat




############################################################################
# Beats per measure
############################################################################
def beats_per_measure_at_tick(tick_value, time_signatures) : 
    '''
    beats_per_measure_at_tick(tick_value, time_signatures)
        tick_value - the tick time at which you and to know the bpmeasure
        time_signatures - a datasctructure you can create with extract_time_signatures(mf) 
    RETURNS: beats per measure, usually the numerator of the current time signature
    '''    
    current_time_signature = meter.TimeSignature('4/4')  # Default to 4/4 if no signature is found
    
    # Find the most recent time signature before the given tick_value
    for tick, time_sig in time_signatures:
        if tick <= tick_value:
            current_time_signature = time_sig
        else:
            break

    return current_time_signature.numerator




############################################################################
# time2tick
############################################################################
TempoEntry = namedtuple("TempoEntry", ("start_ticks", "start_ms", "microsecondsPerTick"))

def getNumber(data, length):
    # Helper function to convert byte string to integer
    return struct.unpack('>I', b'\x00' * (4-length) + data[:length])[0]

################
# Gets the tick number for a clock time value in (an open) music21 MidiFile
# The function tends to get called many times in a tight loop, so assumes the midi file is open and read already
def time2tick(mf, seconds):
    '''
    Gets the tick number for a clock time value in (an open) music21 MidiFile
    time2tick(mf, seconds)
        mf - already read with music21.midi: mf = MidiFile(), mf.open(midi_file), mf.read()
        seconds - the time at which you would like the corresponding tick 
    RETURNS: tick value for a clock time in a midi file
    '''

    ticks_per_quarter = mf.ticksPerQuarterNote
    tempo_events = []
    current_tick = 0
    
    # Collect all tempo change events
    for track in mf.tracks:
        for event in track.events:
            
            if isinstance(event, midi.DeltaTime):
                current_tick += event.time
            elif event.type == midi.MetaEvents.SET_TEMPO:
                mspq = getNumber(event.data, 3)  # microseconds per quarter note
                microsecondsPerTick = float(mspq) / ticks_per_quarter
                if len(tempo_events) == 0:
                    segment_start_ms = current_tick * microsecondsPerTick
                else:
                    last_tempo = tempo_events[-1]
                    segment_start_ms = last_tempo.start_ms + (current_tick - last_tempo.start_ticks) * last_tempo.microsecondsPerTick
                tempo_events.append(TempoEntry(current_tick, segment_start_ms, microsecondsPerTick))
    
    # If no tempo events, use default tempo
    if not tempo_events:
        microsecondsPerTick = 500000 / ticks_per_quarter  # Default 120 BPM
        tempo_events.append(TempoEntry(0, 0, microsecondsPerTick))
    
    # Convert input seconds to microseconds
    target_ms = seconds * 1000000
    
    # Find the tempo segment for the target time
    current_tempo = tempo_events[0]
    for next_tempo in tempo_events[1:]:
        if next_tempo.start_ms > target_ms:
            break
        current_tempo = next_tempo
    
    # Calculate the final tick
    remaining_ms = target_ms - current_tempo.start_ms
    additional_ticks = int(remaining_ms / current_tempo.microsecondsPerTick)
    final_tick = current_tempo.start_ticks + additional_ticks
    
    return final_tick


############################################################################
# tick2time
############################################################################
# Gets the clock time for a particular tick value in (an open) music21 MidiFile
# The function tends to get called many times in a tight loop, so assumes the midi file is open and read already
def tick2time(mf, tick_time):
    '''
    tick2time(mf, tick_time)
        Gets the clock time for a particular tick value in (an open) music21 MidiFile.
        mf - midi file already read with music21.midi: mf = MidiFile(), mf.open(midi_file), mf.read()
        tick_time - tick number at which you would like the corresponding clock time 
    RETURNS: clock time at a particular tick in a midi file
    '''

    ticks_per_quarter = mf.ticksPerQuarterNote
    
    tempo_changes = []
    current_tick = 0
    
    for track in mf.tracks:
        for event in track.events:
            if isinstance(event, midi.DeltaTime):
                current_tick += event.time
            elif event.type == midi.MetaEvents.SET_TEMPO:
                tempo_changes.append((current_tick, tempo.MetronomeMark(number=60000000 // int.from_bytes(event.data, 'big'))))
    
    tempo_changes.sort(key=lambda x: x[0])
    
    if not tempo_changes:
        tempo_changes.append((0, tempo.MetronomeMark(number=120)))
    
    total_seconds = 0
    last_tick = 0
    last_tempo = tempo_changes[0][1]
    
    for change_tick, new_tempo in tempo_changes:
        if change_tick >= tick_time:
            break
        
        tick_duration = change_tick - last_tick
        time_duration = tick_duration * 60 / (last_tempo.number * ticks_per_quarter)
        total_seconds += time_duration
        
        last_tick = change_tick
        last_tempo = new_tempo
    
    remaining_ticks = tick_time - last_tick
    remaining_seconds = remaining_ticks * 60 / (last_tempo.number * ticks_per_quarter)
    
    return total_seconds + remaining_seconds


############################################################################
# FRAMES
############################################################################

class Frame:
    '''
        Frame(num, startTick, startTime, middleTick, middleTime, measure, beat, refframe (number))
        The refframe is the "allignment" with a frame in another rendering of the same piece. 
    '''
    def __init__(self, num=np.nan, sTk=np.nan, sTm=np.nan, mTk=np.nan, mTm=np.nan, measure=np.nan, beat=np.nan, refframe=np.nan):
        self.num = num  # frame number (index in a sequence)
        self.sTk = sTk  # starting tick
        self.sTm = sTm  # starting time
        self.mTk = mTk  # middle tick
        self.mTm = mTm  # middle time
        self.measure = measure  # measure in which the middle of the frame is contained. 
        self.beat = beat  # beat corresponding to middle tick (mTk) 
        self.refframe = refframe  # the best corresponding frame number in a reference file

    ############################
    # The following methods are just for loading and saveing to .npz files for compactness
    ############################
    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def to_dict(self):
        return {attr: getattr(self, attr) for attr in vars(self) if not attr.startswith('_')}

    @classmethod
    def save_frames(cls, frames, fname):
        if not frames:
            raise ValueError("No frames to save")
        
        data = {attr: np.array([getattr(frame, attr) for frame in frames])
                for attr in vars(frames[0]) if not attr.startswith('_')}
        
        fname=addExtensionIfNeeded(fname, 'npz')
        np.savez_compressed(fname, **data)

    @classmethod
    def load_frames(cls, fname):
        fname=addExtensionIfNeeded(fname, 'npz')
        loaded_data = np.load(fname)
        
        frames = []
        for i in range(len(next(iter(loaded_data.values())))):
            frame_data = {key: loaded_data[key][i] for key in loaded_data.keys()}
            frames.append(cls.from_dict(frame_data))
        
        return frames


    # # Usage example for saving and loadiing:
    # Frame.save_frames(frames, 'frames.npz')

    # # Loading frames
    # loaded_frames = Frame.load_frames('frames.npz')

    # # Checking the loaded data
    # for frame in loaded_frames:
    #     print(frame.to_dict())


    def print_short(self):
        return f'({self.num}, mTk={self.mTk}, mTm={self.mTm:.3f}, measure={self.measure:.3f}, beat={self.beat:.3f})'
        
    def __str__(self):
        return f"Frame({self.num}, sTk={self.sTk}, sTm={self.sTm:.3f}, mTk={self.mTk}, mTm={self.mTm:.3f}, measure={self.measure}, beat={self.beat:.3f}, refframe={self.refframe})"
    
    def __repr__(self):
        return f"Frame({self.num}, sTk={self.sTk}, sTm={self.sTm:.3f}, mTk={self.mTk}, mTm={self.mTm:.3f}, measure={self.measure}, beat={self.beat:.3f}, refframe={self.refframe})"



# Creates a list of frames with start, end, and middle tick clock times for a midi file (with its evolving ticks-per-time)
def midi2frameskeleton(midi_file, fps) :

    mf = MidiFile()
    mf.open(midi_file)
    mf.read()


    maxTick=count_total_ticks(midi_file)
    maxTime=tick2time(mf, maxTick)
    
    fdur=1/fps
    halffdur=fdur/2
    
    framelist=[]

    for i, t in enumerate(float_range(0, maxTime, fdur)):
        frame=Frame(i, time2tick(mf,t), round(t, 3), time2tick(mf,t+halffdur), round((t+halffdur), 3), refframe=i)
        framelist.append(frame)
    return framelist

