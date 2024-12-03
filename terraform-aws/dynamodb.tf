resource "aws_dynamodb_table" "ecg_data_raw_table" {
  name         = local.dynamodb_table_name_ecg_raw
  hash_key     = "device_id"
  range_key    = "timestamp_capture_begin"
  billing_mode = "PROVISIONED" # TODO: probably change to on-demand if exceeded
  read_capacity = 25
  write_capacity = 25

  attribute {
    name = "device_id"
    type = "S"
  }

  attribute {
    name = "timestamp_capture_begin"
    type = "S"
  }

  stream_enabled = true
  stream_view_type = "NEW_IMAGE"
}


resource "aws_dynamodb_table" "ecg_abnormality_detection_results_table" {
  name         = local.dynamodb_table_name_ecg_processed
  hash_key     = "device_id"
  range_key    = "timestamp_capture_begin"
  billing_mode = "PROVISIONED" # TODO: probably change to on-demand if exceeded
  read_capacity = 25
  write_capacity = 25

  attribute {
    name = "device_id"
    type = "S"
  }

  attribute {
    name = "timestamp_capture_begin"
    type = "S"
  }

  stream_enabled = true
  stream_view_type = "NEW_IMAGE"
}
