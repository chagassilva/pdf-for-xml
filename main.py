from flask import Flask, request, jsonify, send_file
import pdfplumber
import pytesseract
from PIL import Image
import os
import cv2
import numpy as np
import base64
import io

app = Flask(__name__)
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
        <p>Interface Manual Ativa - Extração de PDF e Imagens</p>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf, .png, .jpg, .jpeg" required>
            <input type="hidden" name="origem_requisicao" value="navegador">
            <input type="submit" value="PROCESSAR ARQUIVO">
        </form>
        <div class="footer">Modo Híbrido: Responde JSON para o n8n e XML para o Navegador.</div>
    </div>
</body>
</html>
'''

def camscanner_filter(img_cv):
    ratio = img_cv.shape[0] / 500.0
    orig = img_cv.copy()
    res = cv2.resize(img_cv, (int(img_cv.shape[1] / ratio), 500))
    
    gray = cv2.cvtColor(res, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 75, 200)
    
    cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
    
    screenCnt = None
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            screenCnt = approx
            break
            
    if screenCnt is not None:
        pts = screenCnt.reshape(4, 2) * ratio
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        (tl, tr, br, bl) = rect
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        # ... (código do Perspective Warp permanece igual)
        dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        
        # A MÁGICA MUDA AQUI: Mantemos a imagem colorida esticada
        warped = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))
        
        # Aplicamos um ganho suave de Contraste (alpha) e Brilho (beta)
        # alpha = 1.2 (20% mais contraste), beta = 15 (um pouco mais claro)
        imagem_limpa = cv2.convertScaleAbs(warped, alpha=1.2, beta=15)
        
        return imagem_limpa
    else:
        # Fallback: Se não achar as quinas, apenas clareia a foto original
        return cv2.convertScaleAbs(orig, alpha=1.2, beta=15)


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    # Rota GET para carregar a página no navegador
    if request.method == 'GET':
        return HTML_PAGE

    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    filename = file.filename.lower()
    
    # Valida se a origem do POST foi o botão HTML da página
    veio_do_navegador = request.form.get('origem_requisicao') == 'navegador'
    
    if file and filename.endswith(('.pdf', '.png', '.jpg', '.jpeg')):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        try:
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>\n<processamento_logistica>\n    <origem>{file.filename}</origem>\n"""
            imagem_processada_b64 = None

            if filename.endswith('.pdf'):
                xml_content += "    <tipo_arquivo>PDF Digital</tipo_arquivo>\n"
                with pdfplumber.open(filepath) as pdf:
                    num_paginas = len(pdf.pages)
                    xml_content += f"    <total_paginas>{num_paginas}</total_paginas>\n    <paginas>\n"
                    for i in range(num_paginas):
                        texto = pdf.pages[i].extract_text(layout=True)
                        texto_limpo = "\n".join([l for l in texto.split('\n') if l.strip()]) if texto else ""
                        xml_content += f'        <pagina numero="{i+1}">\n            <conteudo><![CDATA[\n{texto_limpo}\n]]></conteudo>\n        </pagina>\n'
            else:
                xml_content += "    <tipo_arquivo>Imagem Escaneada (CamScanner API)</tipo_arquivo>\n    <total_paginas>1</total_paginas>\n    <paginas>\n"
                
                img_pil = Image.open(filepath)
                img_cv = np.array(img_pil)
                if len(img_cv.shape) == 3 and img_cv.shape[2] == 4:
                    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGBA2RGB)
                if len(img_cv.shape) == 3:
                    img_cv = img_cv[:, :, ::-1].copy()

                imagem_limpa = camscanner_filter(img_cv)
                
                _, buffer = cv2.imencode('.png', imagem_limpa)
                imagem_processada_b64 = base64.b64encode(buffer).decode('utf-8')
                
                img_final_pil = Image.fromarray(imagem_limpa)
                texto = pytesseract.image_to_string(img_final_pil, config=r'--psm 6 -l por')
                texto_limpo = "\n".join([l for l in texto.split('\n') if l.strip()]) if texto else "Nenhum texto extraído."
                
                xml_content += f'        <pagina numero="1">\n            <conteudo><![CDATA[\n{texto_limpo}\n]]></conteudo>\n        </pagina>\n'

            xml_content += "    </paginas>\n</processamento_logistica>"

            # O grande roteador de resposta
            if veio_do_navegador:
                nome_saida = os.path.splitext(file.filename)[0] + ".xml"
                return send_file(
                    io.BytesIO(xml_content.encode('utf-8')),
                    mimetype='text/xml',
                    as_attachment=True,
                    download_name=nome_saida
                )
            else:
                return jsonify({
                    "status": "sucesso",
                    "xml_data": xml_content,
                    "imagem_base64": imagem_processada_b64
                })

        except Exception as e:
            return jsonify({"erro": str(e)}), 500
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({"erro": "Formato inválido"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)