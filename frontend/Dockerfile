
# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

RUN pip install --no-cache-dir poetry
COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi
COPY . .

# Stage 2: Final image
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app

EXPOSE 8501

CMD ["python", "-m","streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]