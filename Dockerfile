# ---------- 1) FRONTEND BUILD STAGE (Next.js) ----------
FROM node:18 AS frontend-build
WORKDIR /app/frontend

# Copy only frontend files first
COPY frontend/package*.json ./
COPY frontend/next.config.js ./

# Install dependencies
RUN npm install

# Copy rest of frontend
COPY frontend/ .

# Build Next.js as static export
RUN npm run build && npm run export


# ---------- 2) BACKEND + FINAL IMAGE (Python FastAPI) ----------
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for pydantic-core
RUN apt-get update && apt-get install -y \
        build-essential \
        cargo \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend project files
COPY . .

# Copy exported frontend → served by FastAPI
COPY --from=frontend-build /app/frontend/out ./frontend/out

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
