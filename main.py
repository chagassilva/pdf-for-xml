from flask import Flask, request, send_file, render_template_string
import pdfplumber
from pypdf import PdfReader
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'entrada'
OUTPUT_FOLDER = 'AutomacaoPDF'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

HTML_PAGE = '''
<!doctype html>
<title>Conversor PDF para XML</title>
<h1>Enviar PDF para converter</h1>
<form method=post enctype=multipart/form-data>
  <input type=file name=file>
  <input type=submit value=Converter>
</form>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            
            # Lógica de conversão simplificada[cite: 1]
            reader = PdfReader(path)
            xml_paths = []
            
            with pdfplumber.open(path) as pdf:
                for i, page in enumerate(pdf.pages):
                    texto = page.extract_text()
                    if texto:
                        texto_limpo = "\n".join([l.strip() for l in texto.split('\n') if l.strip()])
                        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<processamento_logistica>
    <pagina>{i+1}</pagina>
    <conteudo_extraido><![CDATA[{texto_limpo}]]></conteudo_extraido>
</processamento_logistica>"""
                        xml_name = f"{file.filename}_{i+1}.xml"
                        xml_path = os.path.join(OUTPUT_FOLDER, xml_name)
                        with open(xml_path, "w", encoding="utf-8") as f:
                            f.write(xml_content)
                        xml_paths.append(xml_path)
            
            return f"Processado! {len(xml_paths)} páginas convertidas em {OUTPUT_FOLDER}."
            
    return HTML_PAGE

if __name__ == '__main__':
    # O Easypanel usa a porta 80 por padrão para domínios
    app.run(host='0.0.0.0', port=80)