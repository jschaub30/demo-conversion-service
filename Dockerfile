FROM python:3.10

WORKDIR /app

COPY pyproject.toml .

RUN pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

