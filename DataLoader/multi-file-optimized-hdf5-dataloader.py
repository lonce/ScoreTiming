import torch
from torch.utils.data import Dataset, DataLoader
import h5py
import numpy as np
import json
import os
import random

class MultiFileOptimizedChunkedDataset(Dataset):
    def __init__(self, file_list_or_dir, sample_length):
        self.sample_length = sample_length
        self.file_list = self._get_file_list(file_list_or_dir)
        self.file_data = self._load_file_data()
    
    def _get_file_list(self, file_list_or_dir):
        if isinstance(file_list_or_dir, list):
            return file_list_or_dir
        elif os.path.isdir(file_list_or_dir):
            return [os.path.join(file_list_or_dir, f) for f in os.listdir(file_list_or_dir) if f.endswith('.h5')]
        elif file_list_or_dir.endswith('.txt'):
            with open(file_list_or_dir, 'r') as f:
                return [line.strip() for line in f if line.strip().endswith('.h5')]
        else:
            raise ValueError("Invalid input. Provide a list of file paths, a directory path, or a .txt file with file paths.")

    def _load_file_data(self):
        file_data = []
        for file_path in self.file_list:
            with h5py.File(file_path, 'r') as hf:
                file_data.append({
                    'path': file_path,
                    'total_samples': hf.attrs['total_samples'],
                    'chunk_size': hf.attrs['chunk_size'],
                    'metadata': json.loads(hf.attrs['metadata'])
                })
        return file_data

    def __len__(self):
        return sum(fd['total_samples'] - self.sample_length + 1 for fd in self.file_data)

    def __getitem__(self, idx):
        # Randomly select a file
        file_data = random.choice(self.file_data)
        file_path = file_data['path']
        total_samples = file_data['total_samples']
        chunk_size = file_data['chunk_size']

        # Randomly select a starting index within the file
        start_idx = random.randint(0, total_samples - self.sample_length)

        chunk_idx = start_idx // chunk_size
        local_idx = start_idx % chunk_size

        with h5py.File(file_path, 'r') as hf:
            # Determine if we need to read from two chunks
            if local_idx + self.sample_length > chunk_size:
                # Read from two chunks
                chunk1 = chunk_idx
                chunk2 = chunk_idx + 1
                split_point = chunk_size - local_idx
                
                matrix1_data = np.concatenate([
                    hf['matrix1'][chunk1*chunk_size + local_idx : (chunk1+1)*chunk_size],
                    hf['matrix1'][chunk2*chunk_size : chunk2*chunk_size + (self.sample_length - split_point)]
                ])
                matrix2_data = np.concatenate([
                    hf['matrix2'][chunk1*chunk_size + local_idx : (chunk1+1)*chunk_size],
                    hf['matrix2'][chunk2*chunk_size : chunk2*chunk_size + (self.sample_length - split_point)]
                ])
                vector_data = np.concatenate([
                    hf['teaching_vector'][chunk1*chunk_size + local_idx : (chunk1+1)*chunk_size],
                    hf['teaching_vector'][chunk2*chunk_size : chunk2*chunk_size + (self.sample_length - split_point)]
                ])
            else:
                # Read from a single chunk
                start = chunk_idx * chunk_size + local_idx
                end = start + self.sample_length
                matrix1_data = hf['matrix1'][start:end]
                matrix2_data = hf['matrix2'][start:end]
                vector_data = hf['teaching_vector'][start:end]

        return {
            'matrix1': torch.FloatTensor(matrix1_data),
            'matrix2': torch.FloatTensor(matrix2_data),
            'target': torch.FloatTensor(vector_data),
            'file_path': file_path,
            'start_index': start_idx
        }

# Usage example:
# dataset = MultiFileOptimizedChunkedDataset('/path/to/hdf5/files', sample_length=100)
# dataloader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=4)
