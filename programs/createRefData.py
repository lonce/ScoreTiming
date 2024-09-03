import numpy as np
import argparse
from music21.midi import MidiFile 
import json
import pickle

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.midiscoretools import midi_to_bitmap, extract_time_signatures, count_total_ticks, Frame, loadBitmap, saveBitmap
from modules.midiscoretools import time2tick, tick2time, ticks_per_beat_at_tick, beats_per_measure_at_tick, midi2frameskeleton

###################################
# utilities
###################################




# Grabs the time-positions attribute from the Musescore plugin output mapping clock time to measures and beats
def process_json_loc_file(input_file):
    # Check if the input file exists
    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' not found.")
        return
    
    # Read the JSON data from the file
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Extract the "time-positions" attribute
    time_positions = data.get("time-positions", [])
    return time_positions



# Here we are assigned the "place in the score" to every frame.
# If there were no repeats, we could just count ticks and use PPQ and time signatures to compute, but
# we need the measure information from the musicXML to get the place in the score correctly. 

def measureBeats2frameList(midi_file, measurebeats, frames, verbose=False) : 
	mf = MidiFile()
	mf.open(midi_file)
	mf.read()
    
	PPQ=mf.ticksPerQuarterNote
	time_signatures = extract_time_signatures(midi_file)

	mb_index=0
	mb_maxindex=len(measurebeats)-1

	f_index=0
	next_f_index=1
	f_maxindex=len(frames)-1

	#used as indexes into the meaureBeats elements
	etime=0
	measure=1
	beat=2

	mbindex=0

	previous_measure=0
	previous_beat=0
	previous_beat_tick=0

	done = False

	# Step through each frame either inserting a measure/beat from the list, or interpolating a measure/beat value
	while not done : 
		#  If there is a measurebeat that fits this frames time:
		if (mbindex <= mb_maxindex) and  abs(measurebeats[mbindex][etime] - frames[f_index].mTm) <= abs(measurebeats[mbindex][etime] - frames[next_f_index].mTm) :
			#then assign the measure and beats to the current frame
			frames[f_index].measure = measurebeats[mbindex][measure]
			frames[f_index].beat = measurebeats[mbindex][beat]

			if verbose :
				#print(f'assigned mb[{mbindex}] at {measurebeats[mbindex][etime]} to frame{frames[f_index]}')
				print(f'assigned mb[{mbindex}] at {measurebeats[mbindex][etime]} to frame{frames[f_index].print_short()}')

			#for computing the beat at the midpoint of the next frame
			previous_measure=frames[f_index].measure
			previous_beat=frames[f_index].beat  #this beat gets identified with the middle of the frame
			previous_beat_tick=frames[f_index].mTk

			#step measurebeat index
			mbindex=mbindex+1
            
		else :  #interpolate the measure/beat assignment for the frame based on tick number
			frames[f_index].measure = previous_measure
			# add the number of ticks since last frame divided by ticks_per_beat to get portion of a beat traversed by the frame step
			frames[f_index].beat = previous_beat + (frames[f_index].mTk-previous_beat_tick)/ticks_per_beat_at_tick(frames[f_index].mTk, time_signatures, PPQ)
			            
			#if the beat is in to the next measure, subtact bpmeasure
			bpmeasure =  beats_per_measure_at_tick(frames[f_index].mTk, time_signatures)
			if frames[f_index].beat > bpmeasure + 1 :
			    frames[f_index].beat =  frames[f_index].beat % (bpmeasure + 1) +1
			    
			previous_beat=frames[f_index].beat
			previous_beat_tick=frames[f_index].mTk

		#step both frame indexes
		f_index=f_index+1
		next_f_index=min(next_f_index+1, f_maxindex)
		    
		if f_index > f_maxindex :
			done=True
    
	return frames
    
    



###################################
# main
###################################
def main():
	parser = argparse.ArgumentParser(description="Create Frames and a bitmap representation from a midi file")
	parser.add_argument("-im", "--inputmidi", required=True, help="Input MIDI file")
	parser.add_argument("-il", "--inputlocinf", required=True, help="locinfo from Musescore plugin")
	parser.add_argument("-ob", "--outputbitmap", required=True, help="bitmap representation of midi file")
	parser.add_argument("-of", "--outputframes", required=True, help="Frame data for matching")
	parser.add_argument("-r",  "--rate", type=float, required=True, help="FPS used to slice midi file (defaul 44100/512)")
    
	args = parser.parse_args()
	print(f'createRefData args are {args}')


	# mf = MidiFile()
	# mf.open(midi_file)
	# mf.read()

	# First make the bitmap "score" input for the NN
	bitmap, _, _ = midi_to_bitmap(args.inputmidi, args.rate) 

	###############################################
	# Save the matrix to a binary file in .npy format
	#np.save(args.outputbitmap, bitmap) # adds an npy extension to the save file 
	saveBitmap(args.outputbitmap,bitmap )  #this saves as npz, WAY smaller file size!

	###############################################


	# Now create the "reference frame list" from frame to musical measure and beat
	tmb=process_json_loc_file(args.inputlocinf)
	emptyFrameList=midi2frameskeleton(args.inputmidi,args.rate)
	#------ fill it in with measure and beat info
	refFrameList=measureBeats2frameList(args.inputmidi, tmb, emptyFrameList)
	Frame.save_frames(refFrameList, args.outputframes)
	# # write foo to file
	# with open(args.outputframes + '.pkl', 'wb') as f:
	# 	pickle.dump(refFrameList, f)


	print(f"Processed MIDI file saved as {args.outputbitmap} and {args.outputframes}")

if __name__ == "__main__":
	main()
