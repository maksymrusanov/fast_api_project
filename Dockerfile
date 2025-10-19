
FROM python:3.11-slim AS builder


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        default-libmysqlclient-dev \
        libssl-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim

WORKDIR /app


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        mariadb-client \
        libssl-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin


COPY . .


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

