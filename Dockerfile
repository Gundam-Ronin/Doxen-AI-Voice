# Use official Python 3.10 slim runtime
FROM python:3.10-slim

# Prevent Python from buffering (better logs in Render)
ENV PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install system dependencies required by pydantic-core
RUN apt-get update && apt-get install -y \
    build-essential \
    cargo \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list first (helps leverage Docker caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the image
COPY . .

# Expose the port (Render will map INTERNAL → $PORT)
EXPOSE 10000

# Start your app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
