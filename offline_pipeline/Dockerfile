FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scheduler.py ./scheduler.py
COPY sql/ ./sql/

ENV PYTHONPATH=/app

CMD ["python", "scheduler.py"]
