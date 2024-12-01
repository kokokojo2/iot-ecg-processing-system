resource "aws_iot_topic_rule" "iot_topic_rule" {
  name        = local.iot_core_rule_dynamodb_name
  sql         = "SELECT * FROM '${local.ecg_data_mqtt_topic_name}'"
  sql_version = "2016-03-23"
  enabled = true

  dynamodb {
    table_name     = local.dynamodb_table_name_ecg_raw
    role_arn       = aws_iam_role.iot_core_dynamodb_role.arn
    hash_key_field = "device_id"
    hash_key_value = "$${device_id}"
    range_key_field = "timestamp"
    range_key_value = "$${timestamp}"
  }
}


resource "aws_iam_role" "iot_core_dynamodb_role" {
  name = local.iot_core_dynamodb_role

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "iot.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "iot_core_dynamodb_role_write_policy" {
  name        = local.iot_core_dynamodb_write_policy
  description = "Allow IoT Core to write to DynamoDB."

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:GetItem"
      ],
      "Resource": "${aws_dynamodb_table.ecg_data_raw_table.arn}"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "example_attachment" {
  role       = aws_iam_role.iot_core_dynamodb_role.name
  policy_arn = aws_iam_policy.iot_core_dynamodb_role_write_policy.arn
}


