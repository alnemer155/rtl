FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY shared ./shared
COPY crawler ./crawler
COPY backend ./backend
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --no-cache-dir .[postgres] && mkdir -p /app/data /app/exports

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
