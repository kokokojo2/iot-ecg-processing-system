import os
import json
import numpy as np
import boto3
import logging
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam
import time
from decimal import Decimal
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    format='%(asctime)s: %(levelname)s  %(message)s',
    level=logging.INFO
)

STREAM_NAME = os.getenv('STREAM_NAME')
SHARD_ID = os.getenv('SHARD_ID')
PATH_TO_MODEL = "./model.hdf5"
BATCH_SIZE = 15
DYNAMODB_TABLE_NAME = "ecg-data-chunks-processed"
ABNORMALITIES = ["1dAVb", "RBBB", "LBBB", "SB", "AF", "ST"]

# AWS Clients
dynamodb = boto3.resource("dynamodb")
iot_client = boto3.client("iot-data")
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


def decimal_serializer(obj):
    """
    Custom serializer for Decimal objects.
    Converts Decimal to float; raises TypeError for unsupported types.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def save_full_record_with_prediction(record, prediction):
    """
    Save the full record along with the prediction to DynamoDB and publish to AWS IoT Core.

    Parameters:
    record (dict): The full record from Kinesis.
    prediction (np.array): The prediction result to add to the record.

    Returns:
    None
    """
    try:
        # Convert prediction to Decimal
        record['prediction'] = [Decimal(str(value)) for value in prediction.tolist()]
        record['sampling_rate_hz'] = Decimal(str(record['sampling_rate_hz']))

        # Convert prediction to binary and map abnormalities
        binary_prediction = (prediction > 0.5).astype(int)
        detected_abnormalities = [ABNORMALITIES[i] for i, value in enumerate(binary_prediction) if value == 1]
        record['detected_abnormalities'] = detected_abnormalities

        # Save the full record to DynamoDB
        table.put_item(
            Item=record
        )
        logging.info(f"Saved full record with prediction for Device ID: {record['device_id']}, "
                     f"Timestamp: {record['timestamp_capture_begin']}")

        # Publish record to AWS IoT Core MQTT topic
        topic = f"iot/ecg/{record['device_id']}/chunk-results/"
        iot_client.publish(
            topic=topic,
            qos=1,
            payload=json.dumps(record, default=decimal_serializer)
        )
        logging.info(f"Published record to IoT Core topic: {topic}")
    except Exception as e:
        logging.error(f"Unexpected error while saving record to DynamoDB or publishing to IoT Core: {e}")


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


def predict_on_batch(model, aggregated_data_batch):
    """
    Predict on a batch of ECG samples using the pre-trained model.

    Parameters:
    model: Loaded Keras model for prediction.
    aggregated_data_batch: Batch of ECG data as a NumPy array of shape (batch_size, 4096, 12).

    Returns:
    np.array: Predictions for the input batch.
    """
    y_scores = model.predict(aggregated_data_batch, verbose=0)
    return y_scores


def get_records_from_kinesis(stream_name, shard_id, shard_iterator_type='TRIM_HORIZON'):
    """
    Retrieve up to 15 records at a time from an Amazon Kinesis stream and process them immediately.

    Parameters:
    stream_name (str): Name of the Kinesis stream.
    shard_id (str): Shard ID to consume data from.
    shard_iterator_type (str): Type of shard iterator to use (e.g., 'TRIM_HORIZON', 'LATEST').

    Yields:
    list[dict]: A batch of parsed record data (up to 15 records).
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
            response = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=15)
            shard_iterator = response['NextShardIterator']

            records = response['Records']
            if records:
                parsed_records = [json.loads(record['Data']) for record in records]
                logging.info(f"Retrieved {len(parsed_records)} records from the stream.")
                yield parsed_records

            # Avoid hitting Kinesis read limits
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
        for record_batch in get_records_from_kinesis(stream_name=STREAM_NAME, shard_id=SHARD_ID):
            try:
                # Capture the start of ECS inference
                timestamp_ecs_inference_started = datetime.now(timezone.utc).isoformat()

                # Collect aggregated data and metadata from the batch
                aggregated_data_batch = []

                for record in record_batch:
                    aggregated_data = np.array(record['aggregated_data'])
                    aggregated_data_batch.append(aggregated_data)

                aggregated_data_batch = np.stack(aggregated_data_batch)  # Convert to NumPy array

                logging.info(f"Processing batch of size {len(aggregated_data_batch)}.")
                predictions = predict_on_batch(model, aggregated_data_batch)

                # Capture the end of ECS inference
                timestamp_ecs_inference_finished = datetime.now(timezone.utc).isoformat()

                # Save full records with predictions to DynamoDB and publish to MQTT
                for i, prediction in enumerate(predictions):
                    record = record_batch[i]  # Get the full record
                    del record["aggregated_data"]

                    # Add ECS inference timestamps
                    record['timestamp_ecs_inference_started'] = timestamp_ecs_inference_started
                    record['timestamp_ecs_inference_finished'] = timestamp_ecs_inference_finished

                    save_full_record_with_prediction(record, prediction)

            except Exception as e:
                logging.error(f"Error processing batch: {e}")

    except KeyboardInterrupt:
        logging.info("Shutting down consumer.")
    except Exception as e:
        logging.error(f"Error: {e}")
        raise
