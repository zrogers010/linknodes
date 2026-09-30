FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py registry.json operators.json build_registry.py ./

EXPOSE 8100

# Refresh the feed catalog at container start so deploys always ship the
# current Chainlink directory, then serve. Falls back to the baked-in
# registry.json if the refresh fails (e.g. offline build environments).
CMD ["sh", "-c", "python build_registry.py || echo 'registry refresh failed, using baked-in catalog'; uvicorn main:app --host 0.0.0.0 --port 8100"]
