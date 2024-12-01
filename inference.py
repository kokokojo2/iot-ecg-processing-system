import os
import json
import numpy as np
import boto3
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam


STREAM_NAME = os.getenv('KINESIS_STREAM')
SHARD_ID = os.getenv('SHARD_ID')
SEQUENCE_NUMBER = os.getenv('SEQUENCE_NUMBER')
PATH_TO_MODEL = "./model.hdf5"


def predict_on_data(model, aggregated_data):
    """
    Predict on a single ECG sample using the pre-trained model.

    Parameters:
    model: Loaded Keras model for prediction.
    aggregated_data: ECG data as a NumPy array of shape (4096, 12).

    Returns:
    np.array: Prediction for the input ECG data.
    """
    data = np.expand_dims(aggregated_data, axis=0)  # Shape (1, 4096, 12)
    y_score = model.predict(data, verbose=0)
    return y_score


def get_single_record_from_kinesis(stream_name, shard_id, sequence_number):
    """
    Retrieve a single record from an Amazon Kinesis stream using the sequence number.

    Parameters:
    stream_name (str): Name of the Kinesis stream.
    shard_id (str): Shard ID to consume data from.
    sequence_number (str): Sequence number of the desired record.

    Returns:
    dict: Parsed record data.
    """
    kinesis_client = boto3.client('kinesis')

    shard_iterator = kinesis_client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType='AFTER_SEQUENCE_NUMBER',
        StartingSequenceNumber=sequence_number,
    )['ShardIterator']

    records_response = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=1)
    records = records_response['Records']

    if not records:
        raise ValueError(f"No record found for sequence number {sequence_number}")

    record = json.loads(records[0]['Data'])
    return record


if __name__ == "__main__":
    if not SEQUENCE_NUMBER:
        raise ValueError("SEQUENCE_NUMBER must be provided in the environment variables.")

    model = load_model(PATH_TO_MODEL, compile=False)
    model.compile(loss="binary_crossentropy", optimizer=Adam())

    try:
        print(f"Fetching record from Kinesis stream: {STREAM_NAME}, Shard ID: {SHARD_ID}, Sequence Number: {SEQUENCE_NUMBER}")
        record = get_single_record_from_kinesis(
            stream_name=STREAM_NAME,
            shard_id=SHARD_ID,
            sequence_number=SEQUENCE_NUMBER,
        )

        device_id = record['device_id']
        chunk_idx = record['chunk_idx']
        aggregated_data = np.array(record['aggregated_data'])

        print(f"Received data from device: {device_id}, chunk index: {chunk_idx}, shape: {aggregated_data.shape}.")
        print("Running prediction...")
        prediction = predict_on_data(model, aggregated_data)
        print(f"Prediction: {prediction}")

    except Exception as e:
        print(f"Error: {e}")
        raise
