import json
import sys

import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam

PATH_TO_MODEL = "./model.hdf5"


class KinesisRecordProcessor:
    def __init__(self):
        self.model = load_model(PATH_TO_MODEL, compile=False)
        self.model.compile(loss="binary_crossentropy", optimizer=Adam())
        print("Model loaded successfully.")

    def process_record(self, record):
        """
        Process a single record received from the Kinesis stream.
        """
        try:
            device_id = record['device_id']
            chunk_idx = record['chunk_idx']
            aggregated_data = np.array(record['aggregated_data'])

            print(f"Received data from device: {device_id}, chunk index: {chunk_idx}, shape: {aggregated_data.shape}.")
            print("Running prediction...")
            prediction = self.predict_on_data(aggregated_data)
            print(f"Prediction: {prediction}")
        except Exception as e:
            print(f"Error processing record: {e}")

    def predict_on_data(self, aggregated_data):
        """
        Predict on a single ECG sample using the pre-trained model.
        """
        data = np.expand_dims(aggregated_data, axis=0)  # Shape (1, 4096, 12)
        y_score = self.model.predict(data, verbose=0)
        return y_score

    def run(self):
        """
        Continuously process records from stdin as provided by the Multi-Language Daemon.
        """
        for line in sys.stdin:
            message = json.loads(line)
            action = message.get('action')

            if action == 'initialize':
                print(json.dumps({"action": "status", "responseFor": "initialize", "status": "ok"}))
                sys.stdout.flush()

            elif action == 'processRecords':
                for record in message['records']:
                    try:
                        self.process_record(json.loads(record['data']))
                    except Exception as e:
                        print("Error processing record: {}".format(e))

                print(json.dumps({"action": "status", "responseFor": "processRecords", "status": "ok"}))
                sys.stdout.flush()

            elif action == 'shutdown':
                print(json.dumps({"action": "status", "responseFor": "shutdown", "status": "ok"}))
                sys.stdout.flush()


if __name__ == "__main__":
    processor = KinesisRecordProcessor()
    processor.run()
