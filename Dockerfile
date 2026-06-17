FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN npm install -g supergateway

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8080

CMD ["sh", "-c", "supergateway --stdio 'tp-mcp serve' --port ${PORT:-8080} --ssePath /sse --messagePath /message --cors --healthEndpoints /health"]
