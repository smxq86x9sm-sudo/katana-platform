FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir aiogram==3.13.1 httpx pydantic-settings
COPY . .
RUN mkdir -p /app/data
CMD ["python", "bot.py"]
