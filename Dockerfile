FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Avoid prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    gdal-bin \
    libgdal-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set up virtualenv
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install pip dependencies
COPY pyproject.toml .
COPY README.md .
COPY lumen/ /app/lumen/
COPY dashboard/ /app/dashboard/

RUN pip install --upgrade pip && \
    pip install .

EXPOSE 8000

CMD ["python", "-m", "lumen.cli", "serve", "--port", "8000"]
