FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv gdal-bin python3-gdal \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
