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
# Normally we would run pip install . but skipping heavy install in mock
RUN pip install hatchling fastapi uvicorn pydantic numpy

# Copy project files
COPY lumen/ /app/lumen/

EXPOSE 8000

CMD ["uvicorn", "lumen.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
