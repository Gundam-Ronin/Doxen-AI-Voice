# ============================================================
# 1. BASE BACKEND IMAGE
# ============================================================
FROM python:3.10-slim AS backend

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system deps for pydantic-core
RUN apt-get update && apt-get install -y \
    build-essential \
    cargo \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# ============================================================
# 2. FRONTEND BUILD STAGE (Next.js or Vite)
# ============================================================
FROM node:18-alpine AS frontend

WORKDIR /frontend

# Copy frontend folder only
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .

# Build frontend (Next.js exports to /frontend/out)
RUN npm run build

# ============================================================
# 3. FINAL COMBINED IMAGE
# ============================================================
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copy backend from stage 1
COPY --from=backend /app /app

# Copy frontend static build output into backend
COPY --from=frontend /frontend/out /app/frontend/out

# Expose Render port
EXPOSE 10000

# Start FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
