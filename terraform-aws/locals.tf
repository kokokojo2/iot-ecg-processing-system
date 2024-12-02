locals {
  emulated_iot_device_1_name = "emulated-iot-thing-1"
  iot_core_rule_dynamodb_name = "save_dynamodb_rule"
  ecg_data_mqtt_topic_name = "iot/ecg/data-chunks/"
  iot_core_dynamodb_role = "iot_core_dynamodb_role"
  iot_core_dynamodb_write_policy = "iot-core-dynamodb-allow-write-policy"
  dynamodb_table_name_ecg_raw = "ecg-data-chunks-raw"
  lambda_aggregator_function_name = "ecg-data-parts-aggregator-func"
  kinesis_ecg_chunks_stream_name = "ecg-aggregated-chunks-data-stream"
  ecr_docker_ecg_inference_name = "ecg-docker-inference"
  fargate_cluster_name = "ecg-abnormality-detection-cluster"
  fargate_task_execution_role = "fargate-ecg-task-execution-role"
  fargate_task_container_name = "ecg-inference-container"
  fargate_task_image_uri = "253490759747.dkr.ecr.eu-central-1.amazonaws.com/ecg-docker-inference:latest"
}
