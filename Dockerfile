FROM python:3.9-slim

WORKDIR /app

# Instala dependências do sistema necessárias para o pdfplumber/imagemagick se necessário
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando para manter o container rodando ou executar o script
# ... (restante do arquivo igual)

# Mude de 'seu_script.py' para 'pdf.py' (ou o nome real do seu arquivo)
CMD ["python", "main.py"]