FROM python:3.8-slim

WORKDIR /app

COPY requirements-prod.txt .

RUN pip install --no-cache-dir -r requirements-prod.txt

COPY inference_kcl.py .
COPY data/model.hdf5 .

CMD ["python", "inference_kcl.py"]
