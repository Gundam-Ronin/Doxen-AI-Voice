# Use official Python image
FROM python:3.10-slim

# Prevent Python buffering (better logging)
ENV PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install system dependencies required for pydantic-core
RUN apt-get update && apt-get install -y \
        build-essential \
        cargo \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend project into the image
COPY . .

# Expose the port Render will map
EXPOSE 10000

# Start the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
