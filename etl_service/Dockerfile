FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
RUN mkdir -p logs data/faiss_indexes

ENV PYTHONPATH=/app

CMD ["python", "src/main.py"]