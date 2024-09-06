import argparse
import numpy as np
from scipy import sparse
import h5py
import json
import os
from datetime import datetime

def create_optimized_hdf5(output_path, matrix1, matrix2, gtvector, metadata, chunk_size=100):
    """
    Create an HDF5 file with optimized chunking and indexing.
    
    :param output_path: Path for the output HDF5 file
    :param matrix1: First matrix (will be converted to dense if sparse)
    :param matrix2: Second numpy array
    :param gtvector: Ground truth vector numpy array
    :param metadata: Dictionary containing metadata
    :param chunk_size: Size of chunks for storage and access
    """
    # Convert matrix1 to dense if it's sparse
    if sparse.issparse(matrix1):
        matrix1 = matrix1.toarray()
    
    total_samples = len(gtvector)
    
    with h5py.File(output_path, 'w') as hf:
        # Store matrices and vector with chunking
        hf.create_dataset('matrix1', data=matrix1, chunks=(chunk_size, matrix1.shape[1]), compression="gzip", compression_opts=9)
        hf.create_dataset('matrix2', data=matrix2, chunks=(chunk_size, matrix2.shape[1]), compression="gzip", compression_opts=9)
        hf.create_dataset('gtvector', data=gtvector, chunks=(chunk_size,), compression="gzip", compression_opts=9)
        
        # Create index dataset
        num_chunks = (total_samples + chunk_size - 1) // chunk_size
        index_data = np.arange(num_chunks, dtype=np.int32)
        hf.create_dataset('chunk_index', data=index_data)
        
        # Store metadata
        hf.attrs['metadata'] = json.dumps(metadata)
        
        # Add helpful attributes
        hf.attrs['total_samples'] = total_samples
        hf.attrs['chunk_size'] = chunk_size
        hf.attrs['matrix1_shape'] = matrix1.shape
        hf.attrs['matrix2_shape'] = matrix2.shape
        
        # Store dtype information
        hf.attrs['matrix1_dtype'] = str(matrix1.dtype)
        hf.attrs['matrix2_dtype'] = str(matrix2.dtype)
        hf.attrs['gtvector_dtype'] = str(gtvector.dtype)

    print(f"HDF5 file created successfully: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Create optimized HDF5 file from numpy arrays with metadata from JSON.')
    parser.add_argument('-o', '--output', required=True, help='Output HDF5 file path')
    parser.add_argument('-m1', '--matrix1', required=True, help='Path to first matrix .npz file')
    parser.add_argument('-m2', '--matrix2', required=True, help='Path to second matrix .npz file')
    parser.add_argument('-v', '--gtvector', required=True, help='Path to teaching gtvector .npz file')
#    parser.add_argument('-j', '--json-metadata', required=True, help='Path to JSON file containing metadata')
    parser.add_argument("-j", "--metadata", nargs="?", default=None, help="Path to the variation metadata json")
    parser.add_argument('-c', '--chunk-size', type=int, default=100, help='Chunk size for HDF5 storage')

    args = parser.parse_args()

    # Load numpy arrays
    matrix1 = sparse.load_npz(args.matrix1)  # Assuming the array is stored with scipy.sparse.save_npz
    matrix2 = np.load(args.matrix2)['arr_0'] # Assuming the array is stored with np.savez
    gtvector = np.load(args.gtvector)['arr_0']  # Assuming the array is stored with np.savez


    # Load metadata from JSON file
    with open(args.metadata, 'r') as json_file:
        metadata = json.load(json_file)

    # Add creation date to metadata
    metadata['HDF5 creation_date'] = datetime.now().isoformat()


    print("Metadata type:", type(metadata))
    if isinstance(metadata, dict):
        print("Metadata keys:", list(metadata.keys()))
        for key, value in metadata.items():
            print(f"{key}: {type(value)}")


    create_optimized_hdf5(args.output, matrix1, matrix2, gtvector, metadata, chunk_size=args.chunk_size)

    print(f"Optimized HDF5 file created successfully: {args.output}")

    # Verify the contents of the created file
    with h5py.File(args.output, 'r') as hf:
        print("\nFile contents:")
        print("Keys in the HDF5 file:", list(hf.keys()))
        print("Attributes:", dict(hf.attrs))
        print("Matrix1 shape:", hf['matrix1'].shape)
        print("Matrix2 shape:", hf['matrix2'].shape)
        print("Teaching gtvector length:", len(hf['gtvector']))
        print("Metadata:", json.loads(hf.attrs['metadata']))
        print(f"Chunk size: {hf.attrs['chunk_size']}")
        print(f"Total samples: {hf.attrs['total_samples']}")

    # Compare file sizes
    original_size = os.path.getsize(args.matrix1) + os.path.getsize(args.matrix2) + os.path.getsize(args.gtvector)
    new_size = os.path.getsize(args.output)
    print(f"\nOriginal total size: {original_size / 1024 / 1024:.2f} MB")
    print(f"New HDF5 file size: {new_size / 1024 / 1024:.2f} MB")
    print(f"Size change: {(new_size - original_size) / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
