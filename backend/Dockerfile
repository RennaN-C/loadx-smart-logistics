FROM python:3.12-slim

WORKDIR /app

COPY requirements.lock.txt .

RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2,<27" \
    && python -m pip install --no-cache-dir --require-hashes -r requirements.lock.txt \
    && rm -rf \
        /usr/local/lib/python3.12/site-packages/pip \
        /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
        /usr/local/bin/pip \
        /usr/local/bin/pip3 \
        /usr/local/bin/pip3.12

COPY . .

RUN find . -type f -name "*.py" -exec chmod 0644 {} + \
    && useradd --create-home --uid 10001 loadx \
    && chown -R loadx:loadx /app

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]