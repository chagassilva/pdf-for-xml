FROM python:3.9-slim

WORKDIR /app

# Copia o arquivo de requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as bibliotecas
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos (seu pdf.py ou main.py)
COPY . .

# Expõe a porta que o Flask vai usar
EXPOSE 80

# Comando para rodar (verifique se o nome é pdf.py ou main.py)
CMD ["python", "main.py"]