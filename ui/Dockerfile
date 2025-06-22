FROM python:3.10-slim

WORKDIR /app

# 1) Copy & install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy code & templates
COPY app.py .
COPY templates/ ./templates/

# 3) Expose port & start
EXPOSE 5000
CMD ["python", "app.py"]
