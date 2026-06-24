FROM python:3.9-slim

WORKDIR /app

# Instala apenas o Tesseract e o idioma, sem a lib gráfica obsoleta
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80

CMD ["python", "main.py"]