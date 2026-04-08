FROM python:3.12-slim

WORKDIR /app

# Install DejaVu fonts for Cyrillic PDF support
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create volume mount point for persistent DB
VOLUME ["/app/data"]

# Use data dir for SQLite
ENV DATABASE_URL=sqlite:////app/data/apartment_rental.db

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
