import h5py
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from sklearn.metrics import classification_report, confusion_matrix


def load_ecg_data(path_to_hdf5, dataset_name):
    """
    Load ECG data from the HDF5 file.

    Parameters:
    path_to_hdf5 (str): Path to the HDF5 file.
    dataset_name (str): Name of the dataset within the HDF5 file.

    Returns:
    np.array: ECG data tensor of shape (N, 4096, 12).
    """
    with h5py.File(path_to_hdf5, "r") as f:
        data = f[dataset_name][:]
    return data


def plot_ecg_timeseries(ecg_data, sample_index, lead_names, sampling_rate):
    """
    Plot ECG time series for all 12 leads for a single sample.

    Parameters:
    ecg_data (np.array): ECG data tensor of shape (N, 4096, 12).
    sample_index (int): Index of the sample to visualize.
    lead_names (list): List of lead names.
    """
    # Extract the sample
    sample = ecg_data[sample_index]

    # Generate the time axis
    time_axis = np.linspace(0, 4096 / sampling_rate, 4096)  # Seconds

    # Plot each lead
    plt.figure(figsize=(15, 10))
    for lead in range(12):
        plt.subplot(6, 2, lead + 1)
        plt.plot(time_axis, sample[:, lead])
        plt.title(f"Lead: {lead_names[lead]}")
        plt.xlabel("Time (s)")
        plt.ylabel(r"Amplitude ($\mathrm{10}^{-4} V$)")  # Pretty LaTeX label
        plt.grid(True)
    plt.tight_layout()
    plt.show()


def convert_predictions_to_binary(predictions, threshold=0.5):
    """
    Convert prediction probabilities to binary values using a threshold.

    Parameters:
    predictions (np.array): Prediction probabilities of shape (N, 6).
    threshold (float): Threshold for converting probabilities to binary.

    Returns:
    np.array: Binary predictions of the same shape as input.
    """
    return (predictions >= threshold).astype(int)


def plot_ecg_with_predictions(
    ecg_data, predictions, sample_index, lead_names, sampling_rate, abnormalities
):
    """
    Plot ECG time series for all 12 leads for a single sample and display detected abnormalities.

    Parameters:
    ecg_data (np.array): ECG data tensor of shape (N, 4096, 12).
    predictions (np.array): Model predictions (binary) of shape (N, 6), one column per abnormality.
    sample_index (int): Index of the sample to visualize.
    lead_names (list): List of lead names (default: generic names).
    abnormalities (list): List of abnormalities corresponding to prediction columns.
    sampling_rate (int): Sampling rate in Hz (default: 400 Hz).
    """
    # Extract the sample
    sample = ecg_data[sample_index]
    sample_predictions = predictions[sample_index]

    # Generate the time axis
    time_axis = np.linspace(
        0, sample.shape[0] / sampling_rate, sample.shape[0]
    )  # Adjusted for 400 Hz

    # Create global title with detected abnormalities
    detected_abnormalities = [
        ab for ab, pred in zip(abnormalities, sample_predictions) if pred == 1
    ]
    abnormalities_text = (
        "Detected Abnormalities: " + ", ".join(detected_abnormalities)
        if detected_abnormalities
        else "No Abnormalities Detected"
    )

    # Plot each lead
    plt.figure(figsize=(15, 12))
    for lead in range(12):
        plt.subplot(6, 2, lead + 1)
        plt.plot(time_axis, sample[:, lead])
        plt.title(f"{lead_names[lead]}")
        plt.xlabel("Time (s)")
        plt.ylabel(r"Amplitude ($\mathrm{10}^{-4} V$)")  # Pretty LaTeX label
        plt.grid(True)

    # Add the global title
    plt.suptitle(abnormalities_text, fontsize=16, fontweight="bold", y=0.95)

    plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust layout to fit global title
    plt.show()


def get_classification_report_as_df(annotations, predictions, class_names):
    """
    Generate a classification report as a DataFrame.

    Parameters:
    annotations (np.array): Ground truth labels.
    predictions (np.array): Binary predictions.
    class_names (list): List of class names.

    Returns:
    pd.DataFrame: Classification report as a DataFrame.
    """
    report = classification_report(
        annotations, predictions, target_names=class_names, output_dict=True
    )
    return pd.DataFrame(report).transpose()


def plot_confusion_matrix(annotations, predictions, class_name, class_index):
    """
    Plot the confusion matrix for a specific class.

    Parameters:
    annotations (np.array): Ground truth labels.
    predictions (np.array): Binary predictions.
    class_name (str): Name of the class.
    class_index (int): Index of the class in the arrays.
    """
    cm = confusion_matrix(annotations[:, class_index], predictions[:, class_index])
    plt.figure(figsize=(6, 5))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["No", "Yes"],
        yticklabels=["No", "Yes"],
    )
    plt.title(f"Confusion Matrix for {class_name}")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.show()
