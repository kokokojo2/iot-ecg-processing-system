FROM python:3.8-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    curl \
    && apt-get clean

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY inference_kcl.py .
COPY data/model.hdf5 .

RUN curl -O https://github.com/awslabs/amazon-kinesis-client/releases/download/v2.4.0/amazon-kinesis-client-multilang-daemon-2.4.0.jar
COPY kcl.properties.template kcl.properties

# TODO: refactor env vars replacing to do it in runtime
ENV STREAM_NAME=ecg-aggregated-chunks-data-stream
ENV APPLICATION_NAME=ecg-chunks-processing-app
ENV AWS_REGION=eu-central-1

RUN sed -i "s/<STREAM_NAME>/$STREAM_NAME/" kcl.properties && \
    sed -i "s/<APPLICATION_NAME>/$APPLICATION_NAME/" kcl.properties && \
    sed -i "s/<AWS_REGION>/$AWS_REGION/" kcl.properties

CMD ["java", "-cp", "amazon-kinesis-client-multilang-daemon-2.4.0.jar", "software.amazon.kinesis.multilang.MultiLangDaemon", "kcl.properties"]
