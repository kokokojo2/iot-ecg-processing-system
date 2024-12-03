# README: IoT Device Integration for ECG Processing System

This document provides guidance for IoT device developers to integrate with the ECG processing system. The system leverages AWS resources and performs deep neural network (DNN) inference on ECG data to detect abnormalities.

---

## Overview

The integration involves the following key operations:
1. **Posting ECG Data to AWS IoT Core**
2. **Receiving Processing Results via MQTT**

The system requires devices to authenticate using certificates and follow specific data structures.

---

## 1. Posting Source Data to AWS IoT Core

### AWS IoT Core Details
- **Endpoint**: `a2bivc9dd1ijxx-ats.iot.eu-central-1.amazonaws.com`
- **Authentication**: Certificates-based authentication is mandatory.

### Data Structure Rules
- **Device with ID `physical_iot_device_1`**:
  - The system only accepts **1-lead ECG data**, specifically the **DI lead**.
  - Data is represented as a 1D array of 256 points per part.
- **Other Devices**:
  - The system accepts **12-lead ECG data**, where each part is represented as a 2D array of shape **(256, 12)**:
    - **256 rows**: One row per time step.
    - **12 columns**: Each column represents a lead:
      - `["DI", "DII", "DIII", "AVL", "AVF", "AVR", "V1", "V2", "V3", "V4", "V5", "V6"]`

---

### Data Submission Examples

#### Example for Single-Lead Device (`physical_iot_device_1`):
```json
{
  "device_id": "physical_iot_device_1",
  "timestamp_chunk_sent": "2024-12-03T14:40:27.904Z",
  "chunk_idx": 0,
  "part": 0,
  "sampling_rate_hz": 400,
  "ecg_data": [
    /* 256 points of data for DI lead */
  ],
  "timestamp_capture_begin": "2024-12-03T14:40:27.904Z"
}
```
- **`ecg_data`**: Contains 256 points from the **DI lead**.

#### Example for Multi-Lead Device:
```json
{
  "device_id": "emulated_device_42",
  "timestamp_chunk_sent": "2024-12-03T14:40:27.904Z",
  "chunk_idx": 1,
  "part": 5,
  "sampling_rate_hz": 400,
  "ecg_data": [
    [
      /* DI point */,
      /* DII point */,
      /* DIII point */,
      /* AVL point */,
      /* AVF point */,
      /* AVR point */,
      /* V1 point */,
      /* V2 point */,
      /* V3 point */,
      /* V4 point */,
      /* V5 point */,
      /* V6 point */
    ],
    /* 255 more rows each containing 12 data points for respective leads */
  ],
  "timestamp_capture_begin": "2024-12-03T14:40:27.904Z"
}
```
- **`ecg_data`**: A 2D array with 256 rows (time steps) and 12 columns (leads).

---

### Chunk and Part Logic

To handle large data efficiently, the system processes ECG data in **chunks**. Each chunk contains **4096 points**, and it is divided into **16 parts** of 256 points each.

- **`chunk_idx`**: Represents the chunk number (0, 1, 2, etc.) for consecutive 4096-point segments.
- **`part`**: Represents the part number of the chunk (0 to 15).

#### Workflow:
1. Split each chunk of 4096 points into 16 parts (256 points each).
2. Send each part sequentially with the correct `chunk_idx` and `part` values.
3. Ensure all 16 parts of a chunk are sent for the system to process the data.

> **Important**: The system will only process a chunk after receiving all 16 parts. If any part is missing, the chunk will be ignored.

---

## 2. Receiving Processing Results

IoT devices can subscribe to a dedicated MQTT topic to receive processing results. The topic structure is:

```
iot/ecg/<device_id>/chunk-results/
```

### Response Data Structure
The results will be published in the following JSON format:

```json
{
  "device_id": "physical_iot_device_1",
  "chunk_idx": 0,
  "sampling_rate_hz": 400,
  "timestamp_capture_begin": "2024-12-03T14:40:27.904Z",
  "timestamp_chunk_sent": "2024-12-03T14:40:37.532Z",
  "timestamp_iot_core_rule_triggered": "2024-12-03T12:40:37+00:00",
  "timestamp_lambda_processing_started": "2024-12-03T12:40:22.280189+00:00",
  "timestamp_lambda_processing_finished": "2024-12-03T12:40:43.867756+00:00",
  "timestamp_ecs_inference_started": "2024-12-03T12:40:45.453635+00:00",
  "timestamp_ecs_inference_finished": "2024-12-03T12:40:46.017590+00:00",
  "prediction": [
    1.4243121313484153e-06,
    1.0710035525107742e-07,
    2.6337025360589905e-07,
    4.537741915555671e-07,
    9.485412988397002e-07,
    6.4134764166112745e-09
  ]
}
```

#### Notes:
- **`prediction`**: Array of probabilities for the following abnormalities:
  - `["1dAVb", "RBBB", "LBBB", "SB", "AF", "ST"]`.
- **Binary Predictions**:
  - Probabilities can be converted to binary values using a **threshold of 0.5**.
  - Values ≥ 0.5 indicate the abnormality is present.

---

## Authentication Requirements

All IoT devices must authenticate with AWS IoT Core using valid certificates. Ensure proper configuration of:
- Device certificates
- AWS IoT policy for publish/subscribe actions
- MQTT connection with the endpoint

---

## Key Guidelines

- **Data Validation**: Ensure all required fields are present and formatted correctly before submission.
- **Consistent Sampling Rate**: The sampling rate must always be `400 Hz`.
- **Chunk Management**: Ensure all 16 parts of a chunk are sent with correct `chunk_idx` and `part` values.
- **Lead Compliance**: Ensure the `ecg_data` structure aligns with the device type:
  - **Single-lead devices**: Use 1D arrays for the **DI lead**.
  - **Multi-lead devices**: Use 2D arrays (256 rows, 12 columns) for the specified 12 leads.
- **Testing**: Use a simulator or test environment to validate interactions with AWS IoT Core before deploying on actual devices.

---

This specification ensures smooth integration with the ECG processing cloud system and optimal performance for DNN-based analysis. For support, contact the system administrator or refer to AWS IoT Core documentation.