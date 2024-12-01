import sys
import time
import json
import h5py
from argparse import ArgumentParser
from datetime import datetime
from awsiot import mqtt_connection_builder
from awscrt.mqtt import QoS
from concurrent.futures import Future

import logging
logging.basicConfig(level=logging.INFO)


def parse_arguments():
    """Parse command-line arguments for MQTT connection."""
    parser = ArgumentParser(description="Publish ECG data to AWS IoT Core.")
    parser.add_argument("--endpoint", required=True, help="AWS IoT Core endpoint.")
    parser.add_argument("--client_id", required=True, type=int, help="Client ID suffix (integer).")
    parser.add_argument("--topic", required=True, help="MQTT topic to publish messages to.")
    parser.add_argument("--cert", required=True, help="Path to the device certificate.")
    parser.add_argument("--private_key", required=True, help="Path to the private key.")
    parser.add_argument("--root_ca", required=True, help="Path to the Root CA certificate.")
    parser.add_argument("--hdf5_file", required=True, help="Path to the HDF5 file containing ECG data.")
    parser.add_argument("--dataset_name", required=True, help="Name of the dataset in the HDF5 file.")
    parser.add_argument("--interval", default=0.1, type=int, help="Interval in seconds between data chunks.")
    return parser.parse_args()


def get_ecg_chunks(file_path, dataset_name, chunk_size=1024):
    """
    Generator function to iterate over the entire HDF5 file.
    Yields chunks of the specified size from each record sequentially.

    Args:
        file_path (str): Path to the HDF5 file.
        dataset_name (str): Name of the dataset in the HDF5 file.
        chunk_size (int): Number of data points in each chunk.

    Yields:
        list: A chunk of data with shape (chunk_size, 12).
    """
    with h5py.File(file_path, "r") as f:
        dataset = f[dataset_name]  # Access the dataset
        for chunk_idx, record in enumerate(dataset):  # Iterate over each record in the dataset
            for part, i in enumerate(range(0, record.shape[0], chunk_size)):  # Slice by chunk size
                yield chunk_idx, part, record[i:i+chunk_size, :].tolist()

def prepare_message(client_id, ecg_data, chunk_idx, part):
    """Prepare the JSON message with a timestamp and ECG data."""
    return  {
        "device_id": f"emulated_device_{client_id}",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "chunk_idx": chunk_idx,
        "part": part,
        "ecg_data": ecg_data
    }


def on_connection_interrupted(connection, error, **kwargs):
    print(f"Connection interrupted: {error}")
    raise error


def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed successfully.")


def on_publish_complete(future: Future):
    try:
        future.result()  # Raises an exception if the publish failed
        print("Message published successfully.")
    except Exception as e:
        raise e


def main():
    args = parse_arguments()

    # Reconstruct client ID
    client_id = f"emulated_device_{args.client_id}"

    # Build MQTT connection
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=args.endpoint,
        cert_filepath=args.cert,
        pri_key_filepath=args.private_key,
        ca_filepath=args.root_ca,
        client_id=client_id,
        clean_session=False,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed
    )

    print(f"Connecting to {args.endpoint} with client ID '{client_id}'...")
    connect_future = mqtt_connection.connect()
    connect_future.result()
    print("Connected successfully!")

    try:
        for chunk_idx, part, ecg_chunk in get_ecg_chunks(args.hdf5_file, args.dataset_name, chunk_size=256): # Get (1, 1024, 12) chunk
            message = prepare_message(args.client_id, ecg_chunk, chunk_idx, part)  # Format as JSON
            print(f"Publishing message with chunk_idx={chunk_idx}, data_part={part} at timestamp={message['timestamp']}")
            publish_future = mqtt_connection.publish(
                topic=args.topic,
                payload=json.dumps(message),
                qos=QoS.AT_MOST_ONCE  # Ensure at least once delivery
            )[0]

            publish_future.add_done_callback(on_publish_complete)

            # Wait for the interval before sending the next chunk
            time.sleep(args.interval)

    finally:
        # Disconnect from AWS IoT Core
        print("Disconnecting...")
        disconnect_future = mqtt_connection.disconnect()
        disconnect_future.result()
        print("Disconnected successfully.")


if __name__ == "__main__":
    main()
