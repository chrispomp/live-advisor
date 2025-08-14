# Stage 1: Builder - Install dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Create a non-root user
RUN useradd --create-home --shell /bin/bash nonroot

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements and install dependencies into a virtual environment
COPY --chown=nonroot:nonroot requirements.txt .
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final Image - Copy application and dependencies
FROM python:3.11-slim

WORKDIR /app

# Create the same non-root user
RUN useradd --create-home --shell /bin/bash nonroot

# Copy the virtual environment from the builder stage
COPY --from=builder --chown=nonroot:nonroot /app/venv ./venv

# Copy application code
COPY --chown=nonroot:nonroot server.py .
COPY --chown=nonroot:nonroot common.py .
COPY --chown=nonroot:nonroot system_prompt.txt .

# Set environment to use the venv
ENV PATH="/app/venv/bin:$PATH"

# Switch to the non-root user
USER nonroot

# Expose the port the app runs on (Gunicorn will bind to the PORT env var)
# Cloud Run injects the PORT variable, typically 8080.
EXPOSE 8080

# Run the application with Gunicorn and Uvicorn workers
# The number of workers can be tuned based on performance testing.
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080", "server:app"]