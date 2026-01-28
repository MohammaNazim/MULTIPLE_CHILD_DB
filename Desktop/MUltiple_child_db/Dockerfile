# -----------------------------
# Base image
# -----------------------------
FROM python:3.11-slim

# -----------------------------
# Environment
# -----------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -----------------------------
# Working directory
# -----------------------------
WORKDIR /app

# -----------------------------
# System dependencies
# -----------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Python dependencies
# -----------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# App source
# -----------------------------
COPY . .

# -----------------------------
# Expose port (Cloud Run uses 8080)
# -----------------------------
EXPOSE 8080

# -----------------------------
# Start FastAPI
# -----------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
