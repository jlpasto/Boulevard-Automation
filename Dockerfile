# ---- Base Image ----
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy  
# comes with browsers installed

# ---- Set Workdir ----
WORKDIR /app

# ---- Install Dependencies ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy Code ----
COPY . .

# ---- Expose Port ----
EXPOSE 8000

# ---- Run App ----
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
