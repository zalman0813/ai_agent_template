FROM python:3.11-slim

# Set working directory
WORKDIR /workspace

# Install system dependencies (including WeasyPrint requirements for PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    # WeasyPrint dependencies for PDF generation
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install common Python dependencies for skills
RUN pip install --no-cache-dir \
    requests \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    scipy \
    markdown2 \
    weasyprint

# Keep container running
CMD ["tail", "-f", "/dev/null"]
