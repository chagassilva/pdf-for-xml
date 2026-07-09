from flask import Flask, request, jsonify
import pdfplumber
import pytesseract
from PIL import Image
import os
import cv2
import numpy as np
import base64

app = Flask(__name__)
UPLOAD_FOLDER = 'entrada'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def camscanner_filter(img_cv):
    # 1. Reduz a imagem para a detecção de bordas ficar mais rápida e precisa
    ratio = img_cv.shape[0] / 500.0
    orig = img_cv.copy()
    res = cv2.resize(img_cv, (int(img_cv.shape[1] / ratio), 500))
    
    # 2. Converte para cinza e acha as arestas da folha
    gray = cv2.cvtColor(res, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 75, 200)
    
    # 3. Encontra os maiores contornos (provavelmente a folha de papel)
    cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
    
    screenCnt = None
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        # Se o contorno tem 4 pontas, achamos a DANFE!
        if len(approx) == 4:
            screenCnt = approx
            break
            
    # 4. Faz o recorte e alinhamento (Perspective Warp)
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
        
        dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))
        
        # 5. Aplica o filtro P&B para o texto saltar (AJUSTADO PARA TIRAR O CHUVISCO)
        warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        
        # Filtro mediano: mata o "chuvisco" (ruído) sem borrar as letras
        warped_gray = cv2.medianBlur(warped_gray, 3)
        
        # Aumentamos o bloco de 21 para 51 e a constante de 15 para 20
        # Isso força o algoritmo a olhar para áreas maiores antes de escurecer algo
        limpa = cv2.adaptiveThreshold(
            warped_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 20
        )
        return limpa
    else:
        # Ajuste no Fallback também (caso a foto não ache as quinas)
        gray_orig = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
        gray_orig = cv2.medianBlur(gray_orig, 3)
        return cv2.adaptiveThreshold(
            gray_orig, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 20
        )


@app.route('/', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    filename = file.filename.lower()
    
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

                # Processa a imagem!
                imagem_limpa = camscanner_filter(img_cv)
                
                # Converte a imagem limpa para Base64 para enviar de volta ao n8n
                _, buffer = cv2.imencode('.png', imagem_limpa)
                imagem_processada_b64 = base64.b64encode(buffer).decode('utf-8')
                
                img_final_pil = Image.fromarray(imagem_limpa)
                texto = pytesseract.image_to_string(img_final_pil, config=r'--psm 6 -l por')
                texto_limpo = "\n".join([l for l in texto.split('\n') if l.strip()]) if texto else "Nenhum texto extraído."
                
                xml_content += f'        <pagina numero="1">\n            <conteudo><![CDATA[\n{texto_limpo}\n]]></conteudo>\n        </pagina>\n'

            xml_content += "    </paginas>\n</processamento_logistica>"

            # Devolve um JSON com o XML e a Foto Tratada!
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