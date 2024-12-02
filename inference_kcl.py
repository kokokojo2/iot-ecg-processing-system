import os
import json
import numpy as np
import boto3
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam
import time

# KCL usage should be added later
# now the code uses hardcoded shardId
# as we're running only one instance with no scaling

# anyway we do not need scaling so far
# as the Kinesis data stream scaling should be implemented first
# https://aws.amazon.com/blogs/big-data/auto-scaling-amazon-kinesis-data-streams-using-amazon-cloudwatch-and-aws-lambda/


STREAM_NAME = os.getenv('STREAM_NAME')
SHARD_ID = os.getenv('SHARD_ID')
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


def get_records_from_kinesis(stream_name, shard_id, shard_iterator_type='TRIM_HORIZON'):
    """
    Retrieve records continuously from an Amazon Kinesis stream.

    Parameters:
    stream_name (str): Name of the Kinesis stream.
    shard_id (str): Shard ID to consume data from.
    shard_iterator_type (str): Type of shard iterator to use (e.g., 'TRIM_HORIZON', 'LATEST').

    Yields:
    dict: Parsed record data.
    """
    kinesis_client = boto3.client('kinesis')

    print(f"Getting shard iterator for stream '{stream_name}', shard ID '{shard_id}', "
          f"using iterator type '{shard_iterator_type}'.")

    try:
        shard_iterator = kinesis_client.get_shard_iterator(
            StreamName=stream_name,
            ShardId=shard_id,
            ShardIteratorType=shard_iterator_type,
        )['ShardIterator']
        print("Successfully obtained shard iterator.")
    except Exception as e:
        print(f"Error obtaining shard iterator: {e}")
        raise

    while True:
        try:
            response = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)
            shard_iterator = response['NextShardIterator']

            records = response['Records']
            for record in records:
                print(f"Processing record with data: {record['Data'][:100]}...")ta
                yield json.loads(record['Data'])

            if not records:
                time.sleep(0.5)

        except Exception as e:
            print(f"Error fetching or processing records: {e}")
            time.sleep(1)



if __name__ == "__main__":
    print(f"Loading model from {PATH_TO_MODEL}")
    model = load_model(PATH_TO_MODEL, compile=False)
    print("compiling model.")
    model.compile(loss="binary_crossentropy", optimizer=Adam())

    print(f"Starting to consume records from Kinesis stream: {STREAM_NAME}, Shard ID: {SHARD_ID}")
    try:
        for record in get_records_from_kinesis(stream_name=STREAM_NAME, shard_id=SHARD_ID):
            try:
                device_id = record['device_id']
                chunk_idx = record['chunk_idx']
                aggregated_data = np.array(record['aggregated_data'])

                print(f"Received data from device: {device_id}, chunk index: {chunk_idx}, shape: {aggregated_data.shape}.")
                print("Running prediction...")
                prediction = predict_on_data(model, aggregated_data)
                print(f"Prediction: {prediction}")

            except Exception as e:
                print(f"Error processing record: {e}")

    except KeyboardInterrupt:
        print("Shutting down consumer.")
    except Exception as e:
        print(f"Error: {e}")
        raise
