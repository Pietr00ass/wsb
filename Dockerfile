FROM python:3.10-slim

# Install build tools and dependencies for dlib/face_recognition
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port Railway will use
EXPOSE 5000

# Run the application via Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
