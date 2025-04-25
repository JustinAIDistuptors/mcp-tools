FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY context7_server.py .

# Expose port
EXPOSE 8000

# Set environment variables
ENV PORT=8000
ENV LOG_LEVEL=info

# Run the application
CMD ["uvicorn", "context7_server:app", "--host", "0.0.0.0", "--port", "8000"]
