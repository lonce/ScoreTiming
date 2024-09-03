import argparse
import numpy as np
from bisect import bisect_left

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.midiscoretools import Frame


def find_closest_frame(f1_frames, f2_frame):
    mTk_values = [f.mTk for f in f1_frames]
    idx = bisect_left(mTk_values, f2_frame.mTk)
    if idx == 0:
        return f1_frames[0]
    if idx == len(f1_frames):
        return f1_frames[-1]
    before = f1_frames[idx-1]
    after = f1_frames[idx]
    if after.mTk - f2_frame.mTk < f2_frame.mTk - before.mTk:
        return after
    else:
        return before

def process_frames(f1_frames, f2_frames):
    for f2 in f2_frames:
        closest_f1 = find_closest_frame(f1_frames, f2)
        f2.beat = closest_f1.beat
        f2.measure = closest_f1.measure
        f2.refframe = closest_f1.num
    return f2_frames

def main():
    parser = argparse.ArgumentParser(description="Process two frame files and output matched frames.")
    parser.add_argument("file1", help="Path to the first input file (f1)")
    parser.add_argument("file2", help="Path to the second input file (f2)")
    parser.add_argument("output", help="Path to the output file")
    args = parser.parse_args()

    f1_frames = Frame.load_frames(args.file1)
    f2_frames = Frame.load_frames(args.file2)

    updated_f2_frames = process_frames(f1_frames, f2_frames)
    Frame.save_frames(updated_f2_frames, args.output)

    print(f"Processed frames saved to {args.output}")

if __name__ == "__main__":
    main()