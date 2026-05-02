import pdfplumber
from pypdf import PdfReader, PdfWriter
import os
import xml.etree.ElementTree as ET

def processar_pdfs(pasta_origem="entrada", pasta_saida="AutomacaoPDF"):
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)
    if not os.path.exists(pasta_origem):
        os.makedirs(pasta_origem)
        print(f"Crie a pasta '{pasta_origem}' e coloque seus PDFs lá.")
        return

    arquivos = [f for f in os.listdir(pasta_origem) if f.lower().endswith(".pdf")]

    for arquivo in arquivos:
        pdf_input = os.path.join(pasta_origem, arquivo)
        print(f"Processando: {arquivo}")
        
        try:
            reader = PdfReader(pdf_input)
            for i, page in enumerate(reader.pages):
                num_pagina = i + 1
                
                # Salva página individual (opcional, dependendo do seu volume)
                writer = PdfWriter()
                writer.add_page(page)
                pdf_tmp_path = os.path.join(pasta_saida, f"{arquivo}_p{num_pagina}.pdf")
                with open(pdf_tmp_path, "wb") as f:
                    writer.write(f)

                # Extração e conversão XML
                with pdfplumber.open(pdf_tmp_path) as pdf:
                    texto_bruto = pdf.pages[0].extract_text()
                    if texto_bruto:
                        texto_limpo = "\n".join([l.strip() for l in texto_bruto.split('\n') if l.strip()])
                        
                        # Criando XML estruturado de forma segura
                        root = ET.Element("processamento_logistica")
                        ET.SubElement(root, "pagina").text = str(num_pagina)
                        ET.SubElement(root, "origem").text = arquivo
                        conteudo = ET.SubElement(root, "conteudo_extraido")
                        conteudo.text = texto_limpo # O ElementTree trata caracteres especiais automaticamente

                        xml_path = os.path.join(pasta_saida, f"{arquivo}_p{num_pagina}.xml")
                        tree = ET.ElementTree(root)
                        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
            
            print(f"Sucesso: {arquivo}")
        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")

if __name__ == "__main__":
    processar_pdfs()