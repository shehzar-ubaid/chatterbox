# Base image with Python and CUDA
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Logs ko fauran show karnay kay liye
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y ffmpeg

COPY requirements.txt .

# FIX 100%: 'python3 -m pip' use kiya hay taake exactly usi python mein install ho jo baad mein chalega
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --no-cache-dir runpod
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Apna poora code copy karein
COPY . .

# FIX: Explicitly 'python3' se run karein
CMD ["python3", "-u", "handler.py"]