import os
import json
import boto3

from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone


DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
KINESIS_STREAM_NAME = os.environ.get("KINESIS_STREAM_NAME")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE_NAME)
kinesis = boto3.client("kinesis")

AGGREGATED_DATA_PARTS = 16


def lambda_handler(event, context):
    """
    Lambda handler triggered by DynamoDB Streams or scheduled execution.
    """
    # Capture the processing start time
    lambda_processing_started = datetime.now(timezone.utc).isoformat()

    print("DEBUG: Received event from DynamoDB Streams.")
    print("DEBUG: Event Metadata:")
    print(f"Event ID: {context.aws_request_id}")
    print(f"Function Name: {context.function_name}")
    print(f"Event Source: {event.get('eventSource', 'Unknown')}")
    print(f"Number of Records: {len(event['Records'])}")
    print(f"DEBUG: Print whole event.")

    try:
        for record in event["Records"]:
            print("DEBUG: Processing record metadata:")
            print(f"Event Name: {record['eventName']}")
            print(f"Event Source ARN: {record['eventSourceARN']}")
            print(f"Record Keys: {record['dynamodb'].get('Keys', {})}")

            if record["eventName"] == "INSERT":
                process_new_record(record["dynamodb"]["NewImage"], lambda_processing_started)
    except Exception as e:
        print(f"ERROR: Failed to process event. Exception: {e}")
        raise


def process_new_record(new_image, lambda_processing_started):
    """
    Process a new DynamoDB record to check for aggregation conditions.
    """
    print("DEBUG: Processing new image metadata (excluding ecg_data):")

    device_id = new_image["device_id"]["S"]
    chunk_idx = int(new_image["chunk_idx"]["N"])
    part = int(new_image["part"]["N"])
    timestamp_capture_begin = new_image["timestamp_capture_begin"]["S"]

    print("DEBUG: Extracted necessary fields")
    print("device_id:", device_id)
    print("chunk_idx:", chunk_idx)
    print("part:", part)
    print("timestamp_capture_begin:", timestamp_capture_begin)

    # Skip processing for other parts of the chunk
    # Trigger processing only for 15th part,
    # as we need to aggregate 0-14 parts and join with 15
    if part != 15:
        return

    # Attempt to mark the record as "processing"
    try:
        table.update_item(
            Key={"device_id": device_id, "timestamp_capture_begin": timestamp_capture_begin},
            UpdateExpression="SET processing = :in_progress",
            ConditionExpression="attribute_not_exists(processing)",
            ExpressionAttributeValues={":in_progress": True},
        )
        print(
            f"DEBUG: Successfully marked record as 'processing' for device {device_id}, chunk {chunk_idx}, part {part}."
        )
    except Exception as e:
        print(
            f"DEBUG: Record already processed or in progress for device {device_id}, chunk {chunk_idx}, part {part}. Exiting. Error: {e}"
        )
        return  # Exit if the item is already marked as processing or processed

    aggregate_ecg_data(device_id, chunk_idx, lambda_processing_started)


def aggregate_ecg_data(device_id, chunk_idx, lambda_processing_started):
    """
    Aggregate ECG data for a specific device and chunk from DynamoDB.
    """
    print(
        f"DEBUG: Aggregating ECG data for device {device_id}, chunk index {chunk_idx}."
    )

    # using index here to query efficiently on device_id & chunk_id combination
    response = table.query(
        IndexName="DeviceIdChunkIdxIndex",
        KeyConditionExpression=Key("device_id").eq(device_id) & Key("chunk_idx").eq(chunk_idx),
    )

    items = response["Items"]
    print(
        f"DEBUG: Retrieved {len(items)} items for device {device_id}, chunk {chunk_idx}."
    )

    # Ensure we have all parts (0 through 15)
    parts = sorted([int(item["part"]) for item in items])
    print(f"DEBUG: Retrieved parts: {parts}")
    if parts != list(range(AGGREGATED_DATA_PARTS)):
        print(
            f"DEBUG: Missing parts for device {device_id}, chunk {chunk_idx}. Parts present: {parts}"
        )
        return

    aggregated_data = []
    timestamps_capture_begin = []
    timestamps_chunk_sent = []
    timestamp_iot_rule_triggered = []
    sampling_rates = set()

    for item in sorted(items, key=lambda x: int(x["part"])):
        data = item["ecg_data"]
        if device_id == "physical_iot_device_1":
            # Transform data into a 2D array for this device
            data = [[point] + [0] * 11 for point in data]
        aggregated_data.extend(data)
        timestamps_capture_begin.append(item["timestamp_capture_begin"])
        timestamps_chunk_sent.append(item["timestamp_chunk_sent"])
        sampling_rates.add(item["sampling_rate_hz"])
        timestamp_iot_rule_triggered.append(item["timestamp_iot_core_rule_triggered"])

    if len(sampling_rates) != 1:
        raise ValueError(
            f"ERROR: Inconsistent sampling rates for device {device_id}, chunk {chunk_idx}: {sampling_rates}"
        )

    aggregated_metadata = {
        "sampling_rate_hz": list(sampling_rates)[0],
        "timestamp_capture_begin": min(timestamps_capture_begin),
        "timestamp_chunk_sent": max(timestamps_chunk_sent),
        "timestamp_iot_core_rule_triggered": datetime.fromtimestamp(max(timestamp_iot_rule_triggered) / 1000,
                                                                    timezone.utc).isoformat(),
        "timestamp_lambda_processing_started": lambda_processing_started,
    }

    print(f"DEBUG: Aggregated metadata: {aggregated_metadata}")
    print(f"DEBUG: Aggregated data length: {len(aggregated_data)}")
    if len(aggregated_data) != 4096:
        print(
            f"ERROR: Unexpected data size for device {device_id}, chunk {chunk_idx}: {len(aggregated_data)}"
        )
        return

    # Send the aggregated data to Kinesis
    send_to_kinesis(device_id, chunk_idx, aggregated_data, aggregated_metadata)

    for item in items:
        table.update_item(
            Key={"device_id": item["device_id"], "timestamp_capture_begin": item["timestamp_capture_begin"]},
            UpdateExpression="SET processing = :complete",
            ExpressionAttributeValues={":complete": "done"},
        )
        print(
            f"DEBUG: Marked record as 'complete' for device {device_id}, timestamp_capture_begin {item['timestamp_capture_begin']}."
        )

    print(f"DEBUG: Final metadata with processing times: {aggregated_metadata}")


def decimal_serializer(obj):
    """
    Custom serializer for Decimal objects.
    Converts Decimal to float; raises TypeError for unsupported types.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def send_to_kinesis(device_id, chunk_idx, aggregated_data, aggregated_metadata):
    """
    Send the aggregated ECG data to Kinesis for downstream processing.
    """
    payload = {
        "device_id": device_id,
        "chunk_idx": chunk_idx,
        **aggregated_metadata,  # Add aggregated metadata
    }
    print(
        f"DEBUG: Sending payload to Kinesis (excluding aggregated_data): {json.dumps(payload, default=decimal_serializer)}"
    )

    # Add the aggregated data to the payload
    payload["aggregated_data"] = aggregated_data

    processing_finished = datetime.now(timezone.utc).isoformat()
    payload["timestamp_lambda_processing_finished"] = processing_finished

    serialized_payload = json.dumps(payload, default=decimal_serializer)
    response = kinesis.put_record(
        StreamName=KINESIS_STREAM_NAME, Data=serialized_payload, PartitionKey=device_id
    )
    print(f"DEBUG: Successfully sent data to Kinesis. Response metadata: {response}")
