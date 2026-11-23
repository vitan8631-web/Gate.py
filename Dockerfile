# استخدم صورة بايثون حديثة
FROM python:3.12-slim

# تثبيت المكتبات اللي Playwright والـ Node محتاجينها
RUN apt-get update && apt-get install -y --no-install-recommends \
    libatomic1 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نسخ ملف المتطلبات وتثبيت بايثون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# تثبيت متصفح Chromium الخاص بـ Playwright
RUN playwright install chromium

# نسخ باقي الكود
COPY . .

# تشغيل البوت
CMD ["python", "main.py"]
