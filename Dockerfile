FROM python:3.11.9-slim
WORKDIR /app
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade -r /requirements.txt
CMD ["fastapi", "run", "server.py", "--host", "0.0.0.0", "--port", "8000"]