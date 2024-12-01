locals {
  emulated_iot_device_1_name = "emulated-iot-thing-1"
  iot_core_rule_dynamodb_name = "save_dynamodb_rule"
  ecg_data_mqtt_topic_name = "iot/ecg/data-chunks/"
  iot_core_dynamodb_role = "iot_core_dynamodb_role"
  iot_core_dynamodb_write_policy = "iot-core-dynamodb-allow-write-policy"
  dynamodb_table_name_ecg_raw = "ecg-data-chunks-raw"
  lambda_aggregator_function_name = "ecg-data-parts-aggregator-func"
  kinesis_ecg_chunks_stream_name = "ecg-aggregated-chunks-data-stream"
}
