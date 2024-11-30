import numpy as np
import warnings
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam
from dataset import ECGSequence

warnings.filterwarnings("ignore")


def predict_ecg_samples(
    path_to_hdf5,
    path_to_model,
    dataset_name="tracings",
    output_file="./dnn_output.npy",
    batch_size=32,
):
    """
    Predict ECG samples using a pre-trained model and save the predictions.

    Parameters:
    path_to_hdf5 (str): Path to the HDF5 file containing ECG tracings.
    path_to_model (str): Path to the pre-trained Keras model file.
    dataset_name (str): Name of the dataset within the HDF5 file. Default is 'tracings'.
    output_file (str): Path to save the output predictions. Default is './dnn_output.npy'.
    batch_size (int): Batch size for prediction. Default is 32.

    Returns:
    np.array: Predictions as a NumPy array.
    """
    # Load the ECG sequence
    seq = ECGSequence(path_to_hdf5, dataset_name, batch_size=batch_size)

    # Load the pre-trained model
    model = load_model(path_to_model, compile=False)
    model.compile(loss="binary_crossentropy", optimizer=Adam())

    # Predict on the ECG sequence
    print("Predicting on ECG samples...")
    y_score = model.predict(seq, verbose=1)

    # Save the predictions to a file
    np.save(output_file, y_score)
    print(f"Output predictions saved to {output_file}")

    return y_score


PATH_TO_HDF5 = "./data/ecg_tracings.hdf5"
PATH_TO_MODEL = "./data/model.hdf5"
DATASET_NAME = "tracings"
OUTPUT_FILE = "./data/model_predictions.npy"
BATCH_SIZE = 32


if __name__ == "__main__":
    predictions = predict_ecg_samples(
        path_to_hdf5=PATH_TO_HDF5,
        path_to_model=PATH_TO_MODEL,
        dataset_name=DATASET_NAME,
        output_file=OUTPUT_FILE,
        batch_size=BATCH_SIZE,
    )
