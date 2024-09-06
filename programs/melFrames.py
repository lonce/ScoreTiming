#!/usr/bin/env python3
import soundfile as sf
import numpy as np
import argparse

import librosa

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.midiscoretools import render_wav_with_fluidsynth, Frame, midi2frameskeleton, update_json_metadata

def parse_arguments():

	parser = argparse.ArgumentParser(description="Process MIDI and audio files to produce mel spectrograms and frame data.")
    
	parser.add_argument("root_folder", help="Root folder for all input and output files")
	parser.add_argument("-m", "--midi", required=True, help="Input MIDI file")
	parser.add_argument("-w", "--wave", required=True, help="Input wave file")
	parser.add_argument("-o", "--output-mel", required=True, help="Output mel spectrogram file")
	parser.add_argument("-f", "--output-frames", required=True, help="Output frames file")
	parser.add_argument("--sample_rate", type=int, default=22050, help="Target sample rate (default: 22050)")
	parser.add_argument("--win_length", type=int, default=512, help="Window length for STFT (default: 512)")
	parser.add_argument("--hop_length", type=int, default=256, help="Hop length for STFT (default: 256)")
	parser.add_argument("--n_mels", type=int, default=64, help="Number of mel bands (default: 64)")
	parser.add_argument("--f_min", type=float, default=20.0, help="Minimum frequency for mel bands (default: 20.0)")
	parser.add_argument("-j", "--metadata", nargs="?", default=None, help="Path to the variation metadata json")

	if len(sys.argv) == 1:
		parser.print_help(sys.stderr)
		sys.exit(1)

	return parser.parse_args()


def main():
	"""Produces mel, audio, and frames files for a midi file."""

	try: 
		args = parse_arguments()

		# Join root_folder with file paths
		input_midi = os.path.join(args.root_folder, args.midi)
		wave_file = os.path.join(args.root_folder, args.wave)
		output_mel = os.path.join(args.root_folder, args.output_mel)
		output_frames = os.path.join(args.root_folder, args.output_frames)

		# other arguments:
		sample_rate = args.sample_rate
		win_length = args.win_length
		hop_length = args.hop_length
		n_mels = args.n_mels
		f_min = args.f_min
		f_max = sample_rate / 2  # Calculated based on sample_rate

		##########################################################
		# Midi 2 audio 
		##########################################################
		# fluidsynth writes to wav file, so must write and then read from disk
		render_wav_with_fluidsynth(input_midi, wave_file)
		wave_data, original_sample_rate = sf.read(wave_file)

		# fluidsynth likes to generate stereo, but our midis are not multi channel (that I know of)
		mono_wave_data = wave_data[:, 0]

		# Apply to your audio data
		# Apply to your audio data
		wave_data = mono_wave_data.astype(np.float32)

		if original_sample_rate != sample_rate:
			wave_data = librosa.resample(wave_data, orig_sr=original_sample_rate, target_sr=sample_rate)

		mel_spec = librosa.feature.melspectrogram(
			y=wave_data, 
			sr=sample_rate,
			n_mels=n_mels,
			n_fft=win_length,
			hop_length=hop_length
		)


		# Convert to decibels
		spec_db = librosa.power_to_db(mel_spec, ref=np.max)

		# Save (translating so that each time point is a row - convienient for HDF5 storage and chunking)
		np.savez(output_mel, spec_db.T)
		if (args.metadata != None) : 
			update_json_metadata(args.metadata, {
				"Mel matrix file" : output_mel,
		        "Mel orientation": "time along rows"
		    })



		##########################################################
		# Midi to Frame Lis 
		##########################################################
		frameList=midi2frameskeleton(input_midi,sample_rate/hop_length)
		Frame.save_frames(frameList, output_frames)


		print("melFrames processing complete.")

	except argparse.ArgumentError as e:
		print(f"Error: {e}")
		print("Use --help for more information.")
		sys.exit(2)

if __name__ == "__main__":
	main()