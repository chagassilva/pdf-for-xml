from flask import Flask, request, send_file
import pytesseract
from PIL import Image
import os
import io

app = Flask(__name__)

# Configurações de pastas
UPLOAD_FOLDER = 'entrada'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Defina o caminho do Tesseract se estiver no Windows (Exemplo):
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

HTML_PAGE = '''
<!doctype html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <title>Imagem para XML - Converter</title>
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
        <h1>Conversor Imagem DANFE v1</h1>
        <p>Transforme a FOTO da DANFE em texto estruturado para o Mistral</p>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".png, .jpg, .jpeg" required>
            <input type="submit" value="CONVERTER E BAIXAR XML">
        </form>
        <div class="footer">Processamento com OCR robusto e CDATA seguro.</div>
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

        # Aceita formatos comuns de imagem
        extensoes_validas = ('.png', '.jpg', '.jpeg')
        if file and file.filename.lower().endswith(extensoes_validas):
            img_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(img_path)
            
            try:
                # 1. Abre a imagem usando o Pillow
                img = Image.open(img_path)

                # 2. Configuração mágica do Tesseract (--psm 6 ou 4 ajuda a manter o layout de colunas/tabelas)
                # 'por' define o idioma para Português (reconhece ç, ~, á, etc.)
                config_customizada = r'--psm 6 -l por'
                texto = pytesseract.image_to_string(img, config=config_customizada)
                
                if texto:
                    # Limpa linhas vazias mantendo o alinhamento que o OCR conseguiu pegar
                    texto_limpo = "\n".join([l for l in texto.split('\n') if l.strip()])
                else:
                    texto_limpo = "Nenhum texto pôde ser extraído da imagem."

                # 3. Monta o XML mantendo a sua estrutura original para o Mistral ler
                xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<processamento_logistica>
    <origem>{file.filename}</origem>
    <tipo_arquivo>Imagem escaneada (OCR)</tipo_arquivo>
    <paginas>
        <pagina numero="1">
            <conteudo><![CDATA[
{texto_limpo}
]]></conteudo>
        </pagina>
    </paginas>
</processamento_logistica>"""

                # Envia o arquivo XML gerado direto para o navegador
                nome_saida = os.path.splitext(file.filename)[0] + ".xml"
                return send_file(
                    io.BytesIO(xml_content.encode('utf-8')),
                    mimetype='text/xml',
                    as_attachment=True,
                    download_name=nome_saida
                )

            except Exception as e:
                return f"Erro no processamento do OCR: {str(e)}"
            finally:
                if os.path.exists(img_path):
                    os.remove(img_path) # Deleta a imagem após a conversão
            
    return HTML_PAGE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)