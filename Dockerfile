# --- STAGE 1: Builder ---
# This stage installs all development dependencies needed to compile packages like mysqlclient and cryptography
FROM python:3.11-slim AS builder

# Install system dependencies needed to build cryptography and mysqlclient
# These packages provide the necessary headers and compilers
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        default-libmysqlclient-dev \
        libssl-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- STAGE 2: Final Runtime Image ---
# This stage uses a clean, smaller base image and copies the built packages
FROM python:3.11-slim

WORKDIR /app

# Install only the runtime libraries needed (smaller list)
# We replace versioned libs (libssl3, libffi8) with generic names and use mariadb-client for MySQL runtime.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        mariadb-client \
        libssl-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the built Python packages from the builder stage
# Note: /usr/local/lib/python3.11 is the standard site-packages path in these images
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# *** FIX: Copy the Python executables (like 'uvicorn') into the final image's $PATH ***
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the rest of your application code
COPY . .

# Set the entry point for your FastAPI application
# Replace 'main:app' with the correct path to your FastAPI instance
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

