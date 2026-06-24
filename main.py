from flask import Flask, request, send_file
import pdfplumber
import pytesseract
from PIL import Image
import os
import io

app = Flask(__name__)

# Configurações de pastas
UPLOAD_FOLDER = 'entrada'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML_PAGE = '''
<!doctype html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <title>Motor Híbrido: PDF & Imagem para XML</title>
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
        <h1>Conversor Universal DANFE</h1>
        <p>Aceita PDF digital ou Foto (PNG, JPG) - Saída estruturada para o Mistral</p>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf, .png, .jpg, .jpeg" required>
            <input type="submit" value="PROCESSAR ARQUIVO">
        </form>
        <div class="footer">Roteamento automático: OCR para imagens, Extrator para PDFs.</div>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "Nenhum arquivo enviado", 400
        
        file = request.files['file']
        if file.filename == '':
            return "Nome de arquivo vazio", 400

        filename = file.filename.lower()
        extensoes_validas = ('.pdf', '.png', '.jpg', '.jpeg')
        
        if file and filename.endswith(extensoes_validas):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            
            try:
                # Inicia o XML base
                xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<processamento_logistica>
    <origem>{file.filename}</origem>\n"""

                # ROTA 1: Processamento de PDF
                if filename.endswith('.pdf'):
                    xml_content += "    <tipo_arquivo>PDF Digital</tipo_arquivo>\n"
                    with pdfplumber.open(filepath) as pdf:
                        num_paginas = len(pdf.pages)
                        xml_content += f"    <total_paginas>{num_paginas}</total_paginas>\n"
                        xml_content += "    <paginas>\n"
                        
                        for i in range(num_paginas):
                            texto = pdf.pages[i].extract_text(layout=True)
                            texto_limpo = "\n".join([l for l in texto.split('\n') if l.strip()]) if texto else ""
                            xml_content += f'        <pagina numero="{i+1}">\n            <conteudo><![CDATA[\n{texto_limpo}\n]]></conteudo>\n        </pagina>\n'
                
                # ROTA 2: Processamento de Imagem (OCR)
                else:
                    xml_content += "    <tipo_arquivo>Imagem Escaneada (OCR)</tipo_arquivo>\n"
                    xml_content += "    <total_paginas>1</total_paginas>\n"
                    xml_content += "    <paginas>\n"
                    
                    img = Image.open(filepath)
                    config_customizada = r'--psm 6 -l por'
                    texto = pytesseract.image_to_string(img, config=config_customizada)
                    texto_limpo = "\n".join([l for l in texto.split('\n') if l.strip()]) if texto else "Nenhum texto extraído."
                    
                    xml_content += f'        <pagina numero="1">\n            <conteudo><![CDATA[\n{texto_limpo}\n]]></conteudo>\n        </pagina>\n'

                # Fecha o XML
                xml_content += "    </paginas>\n</processamento_logistica>"

                # Retorna o arquivo gerado
                nome_saida = os.path.splitext(file.filename)[0] + ".xml"
                return send_file(
                    io.BytesIO(xml_content.encode('utf-8')),
                    mimetype='text/xml',
                    as_attachment=True,
                    download_name=nome_saida
                )

            except Exception as e:
                return f"Erro no processamento da automação: {str(e)}", 500
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
            
    return HTML_PAGE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)