# Base image for building dependencies
FROM python:3.10 AS builder

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    postgresql-client \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL library path
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

# Create app directory
WORKDIR /app

# Copy dependency files
COPY Pipfile Pipfile.lock requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

RUN pip install --upgrade pip; pip install pipenv==2023.8.20; pipenv lock \
    && pipenv install --system --dev

# Runtime image
FROM python:3.10 AS runtime

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL library path
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

# Create necessary directories
RUN mkdir -p /app/static/staticfiles /app/static/medias /app/assets/fonts /app/backend/assets/fonts


# Set working directory
WORKDIR /app

# Copy application code
COPY . /app/

# Copy font files to both required locations
COPY ./assets/fonts/*.ttf /app/assets/fonts/
COPY ./assets/fonts/*.ttf /app/backend/assets/fonts/

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
