FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2,<27" \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN find . -type f -name "*.py" -exec chmod 0644 {} + \
    && useradd --create-home --uid 10001 loadx \
    && chown -R loadx:loadx /app

USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
