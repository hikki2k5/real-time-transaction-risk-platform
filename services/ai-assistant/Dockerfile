FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY prompts ./prompts
COPY knowledge ./knowledge
COPY evals ./evals
COPY sql ./sql
COPY scripts ./scripts

ENV AI_ASSISTANT_PORT=8010

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${AI_ASSISTANT_PORT}"]
