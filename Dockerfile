FROM python:3.9-slim

WORKDIR /app

# Atualiza os pacotes do Linux e instala o Tesseract com suporte a Português
# O 'rm -rf /var/lib/apt/lists/*' ajuda a manter a imagem do Docker leve
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as bibliotecas Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos
COPY . .

# Expõe a porta que o Flask vai usar
EXPOSE 80

# Comando para rodar
CMD ["python", "main.py"]