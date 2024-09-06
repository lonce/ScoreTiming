#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

folder="scores/BartokRFD1/"
score="BartokRFD1"
vartag="v001"

# Function to run Python script and check for errors
run_python_script() {
    echo "Running: python $@"  # Print the command with all arguments expanded
    if ! python "$@"; then
        echo "Error: Python script failed: $@"
        exit 1
    fi
}

# Run Python scripts with error checking
run_python_script programs/createRefData.py -im "${folder}RefData/${score}.mid" -il "${folder}RefData/${score}.locinfo.jsn" -ob "${folder}RefData/${score}.bm" -of "${folder}RefData/${score}.frames" -j "${folder}VarData/${vartag}/${score}.metadata.jsn" -r 86.133

run_python_script programs/tempoVariator_time.py -m "${folder}RefData/${score}.mid" -om "${folder}VarData/${vartag}/${score}.${vartag}.mid" -p 5 -a 1 -sp .1 -j "${folder}VarData/${vartag}/${score}.metadata.jsn"

run_python_script programs/melFrames.py "${folder}VarData/${vartag}" -m "${score}.${vartag}.mid" -w "${score}.${vartag}.wav" -o "${score}.${vartag}.mel" -f "${score}.${vartag}.frames" -j "${folder}VarData/${vartag}/${score}.metadata.jsn"

run_python_script programs/frameMatch.py "${folder}RefData/${score}.frames" "${folder}VarData/${vartag}/${score}.${vartag}.frames" "${folder}VarData/${vartag}/${score}.framesout" "${folder}VarData/${vartag}/${score}.${vartag}.gt" -j "${folder}VarData/${vartag}/${score}.metadata.jsn"

run_python_script programs/optimized-hdf5-creator-cli-json-metadata.py -o "${folder}VarData/${vartag}/${score}.${vartag}.h5" -m1 "${folder}RefData/${score}.bm.npz" -m2 "${folder}VarData/${vartag}/${score}.${vartag}.mel.npz" -v "${folder}VarData/${vartag}/${score}.${vartag}.gt.npz" -j "${folder}VarData/${vartag}/${score}.metadata.jsn" --chunk-size 256

echo "All Python scripts completed successfully."

# python programs/createRefData.py -im scores/BartokRFD1/RefData/BartokRFD1.mid -il scores/BartokRFD1/RefData/BartokRFD1.locinfo.jsn -ob scores/BartokRFD1/RefData/BartokRFD1.bm -of scores/BartokRFD1/RefData/BartokRFD1.frames -r 86.133
# python programs/tempoVariator_time.py -m scores/BartokRFD1/RefData/BartokRFD1.mid -om scores/BartokRFD1/VarData/V01/BartokRFD1.${vartag}.mid -p 5 -a 1 -sp .1
# python programs/melFrames.py scores/BartokRFD1/VarData/V01 -m BartokRFD1.${vartag}.mid -w BartokRFD1.${vartag}.wav -o BartokRFD1.${vartag}.mel -f BartokRFD1.${vartag}.frames
# python programs/frameMatch.py scores/BartokRFD1/RefData/BartokRFD1.frames scores/BartokRFD1/VarData/V01/BartokRFD1.${vartag}.frames scores/BartokRFD1/VarData/V01/BartokRFD1.framesout scores/BartokRFD1/VarData/V01/BartokRFD1.gt scores/BartokRFD1/VarData/V01/BartokRFD1.metadata
# python programs/optimized-hdf5-creator-cli-json-metadata.py -o scores/BartokRFD1/VarData/V01/BartokRFD1.${vartag}.h5 -m1 scores/BartokRFD1/RefData/BartokRFD1.bm.npz -m2 scores/BartokRFD1/VarData/V01/BartokRFD1.${vartag}.mel.npz -v scores/BartokRFD1/VarData/V01/BartokRFD1.gt.npz -j scores/BartokRFD1/VarData/V01/BartokRFD1.metadata.jsn --chunk-size 256
