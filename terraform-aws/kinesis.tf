resource "aws_kinesis_stream" "ecg_aggregated_chunks_data" {
  name             = local.kinesis_ecg_chunks_stream_name
  shard_count      = 1
  retention_period = 24 # hours
}