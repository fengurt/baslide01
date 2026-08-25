ARG PYTHON_IMAGE=python:3.13-slim
FROM ${PYTHON_IMAGE}

WORKDIR /app
COPY requirements.txt ./
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt
COPY . .
CMD ["uvicorn", "platform_app.app:app", "--host", "0.0.0.0", "--port", "8765"]
