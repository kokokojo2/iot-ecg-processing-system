import h5py
import numpy as np
import pandas as pd
import time
import warnings
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam

warnings.filterwarnings("ignore")


def benchmark_ecg_model_numpy(
    path_to_hdf5,
    path_to_model,
    dataset_name="tracings",
    batch_sizes=range(1, 101),
    output_csv="./benchmark_results_numpy.csv",
):
    """
    Benchmark ECG model prediction times using NumPy slicing for different batch sizes.

    Parameters:
    path_to_hdf5 (str): Path to the HDF5 file containing ECG tracings.
    path_to_model (str): Path to the pre-trained Keras model file.
    dataset_name (str): Key for the dataset within the HDF5 file. Default is 'tracings'.
    batch_sizes (iterable): Range or list of batch sizes to test. Default is range(1, 101).
    output_csv (str): Path to save the benchmark results. Default is './benchmark_results_numpy.csv'.

    Returns:
    None: Saves benchmark results to a CSV file.
    """
    # Load the ECG tracings data
    with h5py.File(path_to_hdf5, "r") as f:
        tracings = f[dataset_name][:]
        print(f"Loaded data shape: {tracings.shape}")

    # Load the pre-trained model
    model = load_model(path_to_model, compile=False)
    model.compile(loss="binary_crossentropy", optimizer=Adam())

    results = []

    for batch_size in batch_sizes:
        print(f"Testing batch size: {batch_size}")
        # Slice the data to match the batch size
        input_data = tracings[:batch_size]

        # Measure prediction time
        start_time = time.time()
        model.predict(input_data, verbose=0)
        elapsed_time = time.time() - start_time
        print(f"Batch size {batch_size}: {elapsed_time:.4f} seconds")

        # Record the result
        results.append({"Batch Size": batch_size, "Time (seconds)": elapsed_time})

    # Convert results to a DataFrame and save to CSV
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_csv, index=False)
    print(f"Benchmark results saved to {output_csv}")


# Define paths and parameters
PATH_TO_HDF5 = "../data/ecg_tracings.hdf5"
PATH_TO_MODEL = "../data/model.hdf5"
DATASET_NAME = "tracings"
OUTPUT_CSV = "./data/benchmark_results_numpy.csv"
BATCH_SIZES = range(1, 101)

if __name__ == "__main__":
    benchmark_ecg_model_numpy(
        path_to_hdf5=PATH_TO_HDF5,
        path_to_model=PATH_TO_MODEL,
        dataset_name=DATASET_NAME,
        batch_sizes=BATCH_SIZES,
        output_csv=OUTPUT_CSV,
    )
