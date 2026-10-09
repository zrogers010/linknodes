FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py registry.json operators.json ccip_registry.json build_registry.py ./

RUN chown -R appuser:appuser /app

USER appuser

ENV PORT=8080

EXPOSE 8080

CMD sh -c "python build_registry.py 2>/dev/null || echo 'Registry refresh skipped, using baked-in catalog (recommended for stability)'; uvicorn main:app --host 0.0.0.0 --port ${PORT}"
