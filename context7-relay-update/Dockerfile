FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY relay.py .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV LOG_LEVEL=info
ENV UPSTREAM_URL=https://context7-mcp.fly.dev

# Run the application
CMD ["uvicorn", "relay:app", "--host", "0.0.0.0", "--port", "8080"]
