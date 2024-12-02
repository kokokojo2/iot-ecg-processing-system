import os
import json
import numpy as np
import boto3
import logging
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s: %(levelname)s  %(message)s',
    level=logging.INFO
)

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

    logging.info(f"Getting shard iterator for stream '{stream_name}', shard ID '{shard_id}', "
                 f"using iterator type '{shard_iterator_type}'.")

    try:
        shard_iterator = kinesis_client.get_shard_iterator(
            StreamName=stream_name,
            ShardId=shard_id,
            ShardIteratorType=shard_iterator_type,
        )['ShardIterator']
        logging.info("Successfully obtained shard iterator.")
    except Exception as e:
        logging.error(f"Error obtaining shard iterator: {e}")
        raise

    while True:
        try:
            response = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)
            shard_iterator = response['NextShardIterator']

            records = response['Records']
            for record in records:
                logging.info(f"Processing record with data: {record['Data'][:100]}...")  # First 100 chars of data
                yield json.loads(record['Data'])

            # Avoid hitting Kinesis read limits
            if not records:
                time.sleep(0.5)

        except Exception as e:
            logging.error(f"Error fetching or processing records: {e}")
            time.sleep(1)  # Adding delay to avoid potential throttling


if __name__ == "__main__":
    logging.info(f"Loading model from {PATH_TO_MODEL}")
    model = load_model(PATH_TO_MODEL, compile=False)
    logging.info("Compiling model.")
    model.compile(loss="binary_crossentropy", optimizer=Adam())

    logging.info(f"Starting to consume records from Kinesis stream: {STREAM_NAME}, Shard ID: {SHARD_ID}")
    try:
        for record in get_records_from_kinesis(stream_name=STREAM_NAME, shard_id=SHARD_ID):
            try:
                device_id = record['device_id']
                chunk_idx = record['chunk_idx']
                aggregated_data = np.array(record['aggregated_data'])

                logging.info(f"Received data from device: {device_id}, chunk index: {chunk_idx}, shape: {aggregated_data.shape}.")
                logging.info("Running prediction...")
                prediction = predict_on_data(model, aggregated_data)
                logging.info(f"Prediction: {prediction}")

            except Exception as e:
                logging.error(f"Error processing record: {e}")

    except KeyboardInterrupt:
        logging.info("Shutting down consumer.")
    except Exception as e:
        logging.error(f"Error: {e}")
        raise
