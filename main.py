import pdfplumber
from pypdf import PdfReader, PdfWriter
import os
import time

def extrair_para_xml_e_mistral(pdf_input, pasta_saida):
    if not os.path.exists(pdf_input):
        return
        
    try:
        reader = PdfReader(pdf_input)
        if not os.path.exists(pasta_saida):
            os.makedirs(pasta_saida)

        for i, page in enumerate(reader.pages):
            num_pagina = i + 1
            writer = PdfWriter()
            writer.add_page(page)
            
            # Nome do arquivo de saída baseado no original
            nome_base = os.path.basename(pdf_input).replace(".pdf", "")
            pdf_path = os.path.join(pasta_saida, f"{nome_base}_p{num_pagina}.pdf")
            
            with open(pdf_path, "wb") as f:
                writer.write(f)
            
            with pdfplumber.open(pdf_path) as pdf:
                texto_bruto = pdf.pages[0].extract_text()
                if texto_bruto:
                    texto_limpo = "\n".join([l.strip() for l in texto_bruto.split('\n') if l.strip()])
                    
                    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<processamento_logistica>
    <pagina>{num_pagina}</pagina>
    <origem>{pdf_input}</origem>
    <conteudo_extraido><![CDATA[{texto_limpo}]]></conteudo_extraido>
</processamento_logistica>"""
                    
                    xml_path = os.path.join(pasta_saida, f"{nome_base}_p{num_pagina}.xml")
                    with open(xml_path, "w", encoding="utf-8") as f:
                        f.write(xml_content)
        
        print(f"Processado com sucesso: {pdf_input}")
        # Opcional: mover o PDF original para uma pasta 'processados' para não repetir
    except Exception as e:
        print(f"Erro ao processar {pdf_input}: {e}")

# Loop para o servidor não desligar
if __name__ == "__main__":
    PASTA_ENTRADA = "entrada" # Pasta onde você vai jogar os PDFs
    PASTA_SAIDA = "AutomacaoPDF"

    if not os.path.exists(PASTA_ENTRADA): os.makedirs(PASTA_ENTRADA)

    print("Monitorando pasta de entrada...")
    while True:
        arquivos = [f for f in os.listdir(PASTA_ENTRADA) if f.endswith(".pdf")]
        for arquivo in arquivos:
            caminho_completo = os.path.join(PASTA_ENTRADA, arquivo)
            extrair_para_xml_e_mistral(caminho_completo, PASTA_SAIDA)
            # Remove ou move o arquivo após processar para não entrar em loop infinito
            os.remove(caminho_completo) 
        
        time.sleep(10) # Espera 10 segundos antes de verificar novos arquivos