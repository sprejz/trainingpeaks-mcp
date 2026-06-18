FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e . aiohttp

EXPOSE 8080
CMD ["python3", "server.py"]
