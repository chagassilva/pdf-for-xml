import pdfplumber
from pypdf import PdfReader, PdfWriter
import os
import time

def processar_arquivos():
    pasta_entrada = "entrada"
    pasta_saida = "AutomacaoPDF"
    
    # Cria as pastas se não existirem
    if not os.path.exists(pasta_entrada): os.makedirs(pasta_entrada)
    if not os.path.exists(pasta_saida): os.makedirs(pasta_saida)

    # Lista arquivos PDF
    arquivos = [f for f in os.listdir(pasta_entrada) if f.lower().endswith(".pdf")]
    
    if not arquivos:
        return # Sai da função se não houver nada, mas o loop continua

    for arquivo_nome in arquivos:
        caminho_pdf = os.path.join(pasta_entrada, arquivo_nome)
        print(f"Processando: {arquivo_nome}")
        
        try:
            reader = PdfReader(caminho_pdf)
            for i, page in enumerate(reader.pages):
                num_pagina = i + 1
                
                # Extração (usando a lógica do seu código original)
                writer = PdfWriter()
                writer.add_page(page)
                
                # Cria um PDF temporário para a página
                temp_path = os.path.join(pasta_saida, f"temp_{num_pagina}.pdf")
                with open(temp_path, "wb") as f:
                    writer.write(f)
                
                with pdfplumber.open(temp_path) as pdf:
                    texto_bruto = pdf.pages[0].extract_text()
                    if texto_bruto:
                        texto_limpo = "\n".join([l.strip() for l in texto_bruto.split('\n') if l.strip()])
                        
                        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<processamento_logistica>
    <pagina>{num_pagina}</pagina>
    <origem>{arquivo_nome}</origem>
    <conteudo_extraido><![CDATA[{texto_limpo}]]></conteudo_extraido>
</processamento_logistica>"""
                        
                        xml_nome = f"{arquivo_nome}_pag_{num_pagina}.xml"
                        with open(os.path.join(pasta_saida, xml_nome), "w", encoding="utf-8") as f:
                            f.write(xml_content)
                
                os.remove(temp_path) # Limpa o temporário
            
            # Após processar, remove o original da entrada para não processar de novo
            os.remove(caminho_pdf)
            print(f"Sucesso: {arquivo_nome} convertido.")
            
        except Exception as e:
            print(f"Erro no arquivo {arquivo_nome}: {e}")

if __name__ == "__main__":
    print("Servidor de conversão iniciado...")
    while True:
        processar_arquivos()
        time.sleep(10) # Espera 10 segundos para checar de novo