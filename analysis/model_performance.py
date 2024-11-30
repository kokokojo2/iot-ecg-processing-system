import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score

from utils import (
    convert_predictions_to_binary,
    get_classification_report_as_df,
    plot_confusion_matrix,
)


def load_data(model_results_path, annotations_path):
    """
    Load model results and annotations from files.

    Parameters:
    model_results_path (str): Path to the model results (.npy file).
    annotations_path (str): Path to the annotations (CSV file).

    Returns:
    tuple: A tuple containing model results (np.array) and annotations (np.array).
    """
    model_results = np.load(model_results_path)
    annotations = pd.read_csv(annotations_path).values
    return model_results, annotations


if __name__ == "__main__":
    model_results_path = "../data/dnn_output.npy"
    annotations_path = "../data/gold_standard.csv"

    model_results, annotations_array = load_data(model_results_path, annotations_path)

    if model_results.shape != annotations_array.shape:
        raise ValueError("Shapes of model results and annotations do not match.")

    binary_predictions = convert_predictions_to_binary(model_results, threshold=0.5)

    class_names = pd.read_csv(annotations_path).columns.tolist()
    report_df = get_classification_report_as_df(
        annotations_array, binary_predictions, class_names
    )
    print("Classification Report:")
    print(report_df)

    accuracy = accuracy_score(annotations_array, binary_predictions)
    print(f"Accuracy: {accuracy:.4f}")

    for i, class_name in enumerate(class_names):
        plot_confusion_matrix(annotations_array, binary_predictions, class_name, i)
