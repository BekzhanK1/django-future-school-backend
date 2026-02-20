FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (libpq-dev for psycopg2)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directory for SQLite database
RUN mkdir -p /app/data

# Expose port
EXPOSE 9000

# Run Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:9000"]
