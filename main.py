from flask import Flask, request, send_file, render_template_string
import pdfplumber
from pypdf import PdfReader
import os
import io

app = Flask(__name__)

# Configurações de pastas
UPLOAD_FOLDER = 'entrada'
OUTPUT_FOLDER = 'AutomacaoPDF'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# HTML com um visual mais "Pro"
HTML_PAGE = '''
<!doctype html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <title>PDF to XML - Converter</title>
    <style>
        body { font-family: sans-serif; background: #121212; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e1e1e; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); text-align: center; }
        h1 { color: #00ff88; }
        input[type="file"] { margin: 20px 0; display: block; width: 100%; color: #ccc; }
        input[type="submit"] { background: #00ff88; color: #000; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }
        input[type="submit"]:hover { background: #00cc6e; }
        .footer { margin-top: 20px; font-size: 0.8rem; color: #666; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Conversor XML v2</h1>
        <p>Transforme seu PDF para o Mistral</p>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf" required>
            <input type="submit" value="CONVERTER E BAIXAR">
        </form>
        <div class="footer">O arquivo XML será gerado com CDATA seguro.</div>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "Nenhum arquivo enviado"
        
        file = request.files['file']
        if file.filename == '':
            return "Nome de arquivo vazio"

        if file and file.filename.endswith('.pdf'):
            pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(pdf_path)
            
            # Lógica de conversão baseada no seu script original
            try:
                reader = PdfReader(pdf_path)
                num_paginas = len(reader.pages)
                conteudo_completo = ""

                with pdfplumber.open(pdf_path) as pdf:
                    for i in range(num_paginas):
                        texto = pdf.pages[i].extract_text()
                        if texto:
                            texto_limpo = "\n".join([l.strip() for l in texto.split('\n') if l.strip()])
                            conteudo_completo += f"\n--- PAGINA {i+1} ---\n{texto_limpo}"

                # Monta o XML final[cite: 1]
                xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<processamento_logistica>
    <origem>{file.filename}</origem>
    <total_paginas>{num_paginas}</total_paginas>
    <conteudo_extraido><![CDATA[{conteudo_completo}]]></conteudo_extraido>
</processamento_logistica>"""

                # Envia o arquivo direto para o navegador sem salvar lixo no disco permanentemente
                return send_file(
                    io.BytesIO(xml_content.encode('utf-8')),
                    mimetype='text/xml',
                    as_attachment=True,
                    download_name=f"{file.filename.replace('.pdf', '')}.xml"
                )

            except Exception as e:
                return f"Erro no processamento: {str(e)}"
            finally:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path) # Deleta o PDF original após converter
            
    return HTML_PAGE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)