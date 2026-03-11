# Base image with Python and CUDA for GPU support
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

WORKDIR /app

# Install system dependencies like ffmpeg for audio processing
RUN apt-get update && apt-get install -y ffmpeg

# Python packages install karein
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Apna poora code copy karein
COPY . .

# Handler script ko start karein ( -u flag logs ke liye zaroori hai )
CMD ["python", "-u", "handler.py"]