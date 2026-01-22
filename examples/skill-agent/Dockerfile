FROM python:3.11-slim

# Set working directory
WORKDIR /workspace

# Install common dependencies for skills
RUN pip install --no-cache-dir \
    requests \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    scipy \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# Keep container running
CMD ["tail", "-f", "/dev/null"]
