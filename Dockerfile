# Use a lightweight Python version
FROM python:3.10-slim

# 1. Install the missing compilers (The Magic Fix)
RUN apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Set up the app
WORKDIR /app
COPY requirements.txt .

# 3. Install Python libraries
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy your code
COPY . .

# 5. Run the app (Change 'app:app' to your file name, e.g., 'main:app')
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
