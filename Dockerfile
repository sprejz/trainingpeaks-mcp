FROM python:3.12-slim

WORKDIR /app
COPY . .

# .venv ignorieren, sauber installieren
RUN pip install --no-cache-dir -e . aiohttp

# tp-mcp liegt nach pip install -e . in /usr/local/bin
RUN which tp-mcp && tp-mcp --help || echo "tp-mcp not found"

EXPOSE 8080
CMD ["python3", "server.py"]
