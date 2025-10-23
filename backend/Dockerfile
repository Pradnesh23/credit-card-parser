FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies (add gunicorn in case it's not in requirements)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY backend/ ./

EXPOSE 3000

# Run the Flask app with gunicorn for production
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3000", "app:app"]
