FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends bash curl \
  && rm -rf /var/lib/apt/lists/*

COPY default_source_bundle/ /app/default_source_bundle/
COPY src/ /app/src/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "pipeline.run", "--seed", "1001", "--user-count", "100", "--timeline-ticks", "30", "--items-per-session", "12", "--max-candidate-pool-size", "80", "--output-dir", "/app/output/default_run"]
