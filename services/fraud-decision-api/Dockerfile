FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY services/fraud-decision-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/fraud-decision-api/app ./app
COPY pipelines/training/model-artifacts/fraud-risk-model ./model-artifacts/fraud-risk-model

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
