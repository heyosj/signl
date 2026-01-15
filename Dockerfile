FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config.example.yaml .

# Config should be mounted at runtime
# docker run -v ./config.yaml:/app/config.yaml -v ./state.json:/app/state.json

CMD ["python", "-m", "src.main"]
