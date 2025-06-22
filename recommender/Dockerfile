# Recommender runs on Python 3.10 slim
FROM python:3.10-slim

WORKDIR /app

# 1) Copy & install only what you need
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy the main script
COPY run_recommend.py .

# 3) Default command
CMD ["python", "run_recommend.py"]
