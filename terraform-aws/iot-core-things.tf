resource "aws_iot_thing" "emulated_iot_thing_1" {
  name = local.emulated_iot_device_1_name
}

resource "aws_iot_policy" "emulated_iot_thing_1_policy" {
  name   = "${local.emulated_iot_device_1_name}-policy"
  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:Publish",
        "iot:Subscribe",
        "iot:Receive",
        "iot:Connect"
      ],
      "Resource": "*"
    }
  ]
}
POLICY
}

resource "aws_iot_certificate" "emulated_iot_thing_1_cert" {
  active = true
}

resource "aws_iot_policy_attachment" "emulated_iot_thing_1_policy_attach" {
  policy = aws_iot_policy.emulated_iot_thing_1_policy.name
  target = aws_iot_certificate.emulated_iot_thing_1_cert.arn
}

resource "aws_iot_thing_principal_attachment" "emulated_iot_thing_1_principal_attach" {
  thing     = aws_iot_thing.emulated_iot_thing_1.name
  principal = aws_iot_certificate.emulated_iot_thing_1_cert.arn
}


