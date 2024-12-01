resource "aws_lambda_function" "ecg_chunks_aggregator_func" {
  filename      = "../lambda_aggregation.zip"
  function_name = local.lambda_aggregator_function_name
  role          = aws_iam_role.ecg_chunks_aggregator_func_execution_role.arn
  handler       = "lambda_aggregation.lambda_handler"
  runtime       = "python3.9"
  timeout       = 60
  memory_size   = 128

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.ecg_data_raw_table.name
      KINESIS_STREAM_NAME = aws_kinesis_stream.ecg_aggregated_chunks_data.name
    }
  }
}

resource "aws_lambda_event_source_mapping" "ecg_chunks_aggregator_func_dynamodb_trigger" {
  event_source_arn  = aws_dynamodb_table.ecg_data_raw_table.stream_arn
  function_name     = aws_lambda_function.ecg_chunks_aggregator_func.arn
  starting_position = "LATEST"
}


resource "aws_iam_role_policy_attachment" "ecg_chunks_aggregator_func_policy_attachment" {
  role       = aws_iam_role.ecg_chunks_aggregator_func_execution_role.name
  policy_arn = aws_iam_policy.ecg_chunks_aggregator_func_policy.arn
}

resource "aws_iam_role" "ecg_chunks_aggregator_func_execution_role" {
  name = "${local.lambda_aggregator_function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "ecg_chunks_aggregator_func_policy" {
  name        = "${local.lambda_aggregator_function_name}-policy"
  description = "IAM policy for Lambda to interact with DynamoDB and Kinesis."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:PutItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.ecg_data_raw_table.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:DescribeStream",
          "dynamodb:ListStreams"
        ]
        Resource = aws_dynamodb_table.ecg_data_raw_table.stream_arn
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord"
        ]
        Resource = aws_kinesis_stream.ecg_aggregated_chunks_data.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}



