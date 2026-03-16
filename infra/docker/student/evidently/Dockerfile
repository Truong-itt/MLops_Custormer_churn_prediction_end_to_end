FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir evidently==0.4.38

EXPOSE 8001

CMD ["evidently", "ui", "--workspace", "/workspace", "--host", "0.0.0.0", "--port", "8001"]
