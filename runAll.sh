#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

folder="scores/BartokRFD1/"
score="BartokRFD1"
vardir="V01/"

# Function to run Python script and check for errors
run_python_script() {
    if ! python "$@"; then
        echo "Error: Python script failed: $@"
        exit 1
    fi
}

# Run Python scripts with error checking
run_python_script programs/createRefData.py -im "${folder}RefData/${score}.mid" -il "${folder}RefData/${score}.locinfo.jsn" -ob "${folder}RefData/${score}.bm" -of "${folder}RefData/${score}.frames" -r 86.133

run_python_script programs/tempoVariator_time.py -m "${folder}RefData/${score}.mid" -om "${folder}VarData/${vardir}/${score}v01.mid" -p 5 -a 1 -sp .1

run_python_script programs/melFrames.py "${folder}VarData/${vardir}" -m "${score}v01.mid" -w "${score}v01.wav" -o "${score}v01.mel" -f "${score}v01.frames"

run_python_script programs/frameMatch.py "${folder}RefData/${score}.frames" "${folder}VarData/${vardir}/${score}v01.frames" "${folder}VarData/${vardir}/${score}framesout"

echo "All Python scripts completed successfully."