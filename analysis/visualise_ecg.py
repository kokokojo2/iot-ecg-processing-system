import numpy as np

from analysis.utils import (
    load_ecg_data,
    plot_ecg_timeseries,
    convert_predictions_to_binary,
    plot_ecg_with_predictions,
)
from analysis.constants import LEAD_NAMES, ABNORMALITIES, SAMPLING_RATE

path_to_hdf5 = "../data/ecg_tracings.hdf5"
path_to_predictions = "../data/dnn_output.npy"
dataset_name = "tracings"

ecg_data = load_ecg_data(path_to_hdf5, dataset_name)
plot_ecg_timeseries(
    ecg_data,
    sample_index=0,
    lead_names=LEAD_NAMES,
    sampling_rate=SAMPLING_RATE,
)

ecg_data = load_ecg_data(path_to_hdf5, dataset_name)
predictions_prob = np.load(path_to_predictions)

predictions_binary = convert_predictions_to_binary(predictions_prob, threshold=0.5)

plot_ecg_with_predictions(
    ecg_data=ecg_data,
    predictions=predictions_binary,
    sample_index=0,
    lead_names=LEAD_NAMES,
    abnormalities=ABNORMALITIES,
    sampling_rate=SAMPLING_RATE,
)
