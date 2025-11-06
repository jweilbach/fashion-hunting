# Minimal Docker image for Phase 1
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
WORKDIR /app/backend
CMD ["python", "src/fetch_and_report.py"]
