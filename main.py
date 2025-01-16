from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests
import fitz
import pymupdf
import os
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import base64
import subprocess

# Configuração do Flask
app = Flask(__name__)

# Configuração do Logging
log_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Configura o handler para salvar logs em arquivo
file_handler = RotatingFileHandler("app.log", maxBytes=10000000, backupCount=5)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

# Configura o handler para console
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG)

# Adiciona os handlers ao logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


load_dotenv()
CODIGO_BITRIX = os.getenv("CODIGO_BITRIX")
CODIGO_BITRIX_STR = os.getenv("CODIGO_BITRIX_STR")
PROFILE = os.getenv("PROFILE")
BASE_URL_API_BITRIX = os.getenv("BASE_URL_API_BITRIX")


def upload_file_to_bitrix(deal_id, file_name, encoded_file):
    url = f"{BASE_URL_API_BITRIX}/{PROFILE}/{CODIGO_BITRIX}/crm.deal.update"

    fields = {"UF_CRM_1723580499": {"fileData": [file_name, encoded_file]}}

    params = {"REGISTER_SONET_EVENT": "N"}

    headers = {"Content-Type": "application/json"}

    payload = {"id": deal_id, "fields": fields, "params": params}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("result"):
            print(f"Deal updated successfully. ID: {data['result']}")
        else:
            print(f"Failed to update deal. Error: {data.get('error')}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to communicate with Bitrix24 API: {e}")


def file_to_base64(file_path):
    with open(file_path, "rb") as file:
        file_data = file.read()
        base64_encoded = base64.b64encode(file_data).decode("utf-8")
        return base64_encoded


def obter_dados_bitrix(campos_ids, negocio_id):
    url = f"{BASE_URL_API_BITRIX}/{PROFILE}/{CODIGO_BITRIX}/crm.deal.get"
    params = {"ID": negocio_id}
    dados_obtidos = {}
    try:
        logger.info(f"Obtendo dados do Bitrix24 para o negócio ID: {negocio_id}")
        resposta = requests.get(url, params=params)
        resposta.raise_for_status()
        dados = resposta.json()
        resultado = dados.get("result", {})
        for campo_id in campos_ids:
            dados_obtidos[campo_id] = resultado.get(campo_id, "Campo não encontrado")
        logger.info("Dados do Bitrix24 obtidos com sucesso.")
    except requests.RequestException as e:
        logger.error(f"Erro ao obter dados do Bitrix24: {e}")
        for campo_id in campos_ids:
            dados_obtidos[campo_id] = "Erro"
    return dados_obtidos


def retornar_campos_com_valores(pdf_path):
    logger.info(f"Retornando campos e valores do PDF: {pdf_path}")
    documento = fitz.open(pdf_path)
    campos = {}
    for pagina in documento:
        for widget in pagina.widgets():
            campo_nome = widget.field_name
            campo_tipo = widget.field_type
            campo_valor = widget.field_value if widget.field_value else "Campo vazio"
            if campo_nome:
                campos[campo_nome] = (campo_tipo, campo_valor)
    documento.close()
    logger.info("Campos e valores do PDF retornados com sucesso.")
    return campos


def preencher_campos(pdf_path, novos_campos_valores, name_card):
    logger.info(f"Preenchendo campos no PDF: {pdf_path}")
    documento = fitz.open(pdf_path)
    for pagina in documento:
        for widget in pagina.widgets():
            campo_nome = widget.field_name
            if campo_nome in novos_campos_valores:
                novo_valor = novos_campos_valores[campo_nome]
                logger.debug(
                    f"Atualizando campo '{campo_nome}' de '{widget.field_value}' para '{novo_valor}'"
                )
                widget.field_value = novo_valor

                if widget.field_name == "Bot#C3#A3o de op#C3#A7#C3#A3o 1_2":
                    print(widget)
                widget.update()
    novo_pdf_path = f"{name_card}" + pdf_path.split("\\")[-1]
    documento.save(novo_pdf_path)
    documento.close()
    logger.info(f"PDF atualizado salvo em: {novo_pdf_path}")


def formatar_data_para_pdf(data_iso):
    try:
        data_obj = datetime.fromisoformat(data_iso.split("+")[0])
        data_formatada = data_obj.strftime("%d-%m-%Y")
        return data_formatada
    except ValueError:
        logger.error(f"Formato de data inválido: {data_iso}")
        return ""


def separar_data(data_str):
    try:
        data_obj = datetime.strptime(data_str, "%d-%m-%Y")
        dia = data_obj.strftime("%d")
        mes = data_obj.strftime("%m")
        ano = data_obj.strftime("%Y")
        return dia, mes, ano
    except ValueError:
        logger.error(f"Formato de data inválido: {data_str}")
        return "", "", ""


def obter_partes_data(data_str):
    data_formatada = formatar_data_para_pdf(data_str)
    return separar_data(data_formatada)


def atualizar_valores_com_base_no_status(dados_bitrix, novos_campos_valores):
    status = dados_bitrix.get("UF_CRM_1713214941", None)
    if isinstance(status, list):
        status = status[0] if status else ""
    status = str(status).strip()
    logger.debug(f"Valor obtido para UF_CRM_1713214941: '{status}'")
    if status == "48466":
        novos_campos_valores["tres"] = "Yes"  # 300
    elif status == "48468":
        novos_campos_valores["quatro"] = "Yes"  # 400
    elif status == "48470":
        novos_campos_valores["cinco"] = "Yes"  # 500
    elif status == "34668":
        novos_campos_valores["seis"] = "Yes"  # 600
    elif status == "48474":
        novos_campos_valores["sete"] = "Yes"  # 700
    elif status == "48476":
        novos_campos_valores["oito"] = "Yes"  # 800
    elif status == "48478":
        novos_campos_valores["giga_um"] = "Yes"  # 1000
    else:
        logger.warning(f"Status '{status}' não corresponde a nenhum valor conhecido.")

    # novos_campos_valores['tres'] = "Yes" #300
    # novos_campos_valores['quatro'] = "Yes" #400
    # novos_campos_valores['cinco'] = "Yes" #500
    # novos_campos_valores['seis'] = "Yes" #600
    # novos_campos_valores['sete'] = "Yes" #700
    # novos_campos_valores['oito'] = "Yes" #800
    # novos_campos_valores['giga_um'] = "Yes" #1000

    novos_campos_valores["Caixa de sele#C3#A7#C3#A3o 11"] = "Yes"
    novos_campos_valores["Caixa de sele#C3#A7#C3#A3o 12_3"] = "Yes"
    novos_campos_valores["Caixa de sele#C3#A7#C3#A3o 15_2"] = "Yes"

    for i in range(7):
        novos_campos_valores[f"ciente{i}"] = "Yes"

    return novos_campos_valores


def validar_cep(cep):
    cep_limpio = "".join(c for c in cep if c.isdigit())
    if len(cep_limpio) == 8:
        return cep_limpio
    else:
        logger.warning(f"CEP inválido: {cep}")
        return ""


def obter_cidade_por_cep(cep):
    cep = validar_cep(cep)
    if not cep:
        return ""
    url = f"https://viacep.com.br/ws/{cep}/json/"
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        if "erro" in dados:
            logger.warning(f"CEP {cep} não encontrado.")
            return ""
        cidade = dados.get("localidade", "")
        return cidade
    except requests.RequestException as e:
        logger.error(f"Erro ao obter cidade para CEP {cep}: {e}")
        return ""


def obter_estado_por_cep(cep):
    cep = validar_cep(cep)
    if not cep:
        return ""
    url = f"https://viacep.com.br/ws/{cep}/json/"
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        if "erro" in dados:
            logger.warning(f"CEP {cep} não encontrado.")
            return ""
        estado = dados.get("uf", "")
        return estado
    except requests.RequestException as e:
        logger.error(f"Erro ao obter estado para CEP {cep}: {e}")
        return ""


def atualizar_campos_com_localizacao(dados_bitrix, novos_campos_valores):
    cep = dados_bitrix.get("UF_CRM_1700661314351", "")
    cidade = obter_cidade_por_cep(cep)
    estado = obter_estado_por_cep(cep)
    if cidade:
        novos_campos_valores["Caixa de texto 13"] = cidade
    else:
        novos_campos_valores["Caixa de texto 13"] = "CEP não encontrado"
    if estado:
        novos_campos_valores["Caixa de texto 14"] = estado
    else:
        novos_campos_valores["Caixa de texto 14"] = "CEP não encontrado"
    return novos_campos_valores


def atualizar_campos_com_base_no_id(dados_bitrix, novos_campos_valores):
    campo_id = dados_bitrix.get("UF_CRM_1724096872", None)
    if campo_id == "48550":
        novos_campos_valores["masc"] = "Yes"
    elif campo_id == "48548":
        novos_campos_valores["fem"] = "Yes"
    return novos_campos_valores

def file_to_base64(file_path):
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")

import subprocess
import os

def comprimir_pdf_com_ghostscript(input_path, output_path):
    """
    Comprime o arquivo PDF usando Ghostscript.
    """
    try:
        command = [
            "gswin64c",  # Certifique-se de que o Ghostscript está instalado e configurado no PATH
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",  # Nível de compressão (pode usar /screen, /ebook, /printer ou /prepress)
            "-dNOPAUSE",
            "-dBATCH",
            "-dQUIET",
            f"-sOutputFile={output_path}",
            input_path,
        ]

        subprocess.run(command, check=True)
        return output_path
    except Exception as e:
        logger.error(f"Erro ao comprimir o PDF com Ghostscript: {e}")
        return input_path


@app.route("/processar", methods=["POST"])
def processar():
    negocio_id = request.args.get("negocio_id")
    pdf_path = "Termo Algar Telecom.pdf"

    if not negocio_id or not pdf_path:
        logger.error("Parâmetros inválidos fornecidos.")
        return jsonify({"erro": "Parâmetros inválidos."}), 400

    campos_ids = {
        "UF_CRM_1697762313423": "Nome",
        "UF_CRM_1723557410": "Data (dia, mês, ano)",
        "UF_CRM_1697807353336": "CPF",
        "UF_CRM_1697807372536": "RG",
        "UF_CRM_1697763267151": "Nome da mãe",
        "UF_CRM_1698698407472": "Telefone de contato",
        "UF_CRM_1697807340141": "Email",
        "UF_CRM_1698688252221": "Endereço",
        "UF_CRM_1700661252544": "Número",
        "UF_CRM_1700661287551": "Bairro",
        "UF_CRM_1700661275591": "Complemento",
        "UF_CRM_1709042046": "Cidade",
        "UF_CRM_1700661314351": "CEP",
        "UF_CRM_1713214941": "Status",
        "UF_CRM_1706040523430": "Data da Venda",
        "OPPORTUNITY": "Valor e Moeda",
        "UF_CRM_1724096872": "ID do campo adicional",
    }

    dados_bitrix = obter_dados_bitrix(campos_ids.keys(), negocio_id)
    data_str = dados_bitrix.get("UF_CRM_1723557410", "")
    dia, mes, ano = obter_partes_data(data_str)

    novos_campos_valores = {
        "Caixa de texto 8": dados_bitrix.get("UF_CRM_1697807340141", ""),
        "dinheiro": dados_bitrix.get("OPPORTUNITY", ""),
        "Caixa de texto 1": dados_bitrix.get(
            "UF_CRM_1697762313423", "Campo não encontrado"
        ),
        "Caixa de texto 5": dia,
        "Caixa de texto 6": mes,
        "Caixa de texto 7": ano,
        "Caixa de texto 3": dados_bitrix.get("UF_CRM_1697807353336", ""),
        "Caixa de texto 2": dados_bitrix.get("UF_CRM_1697807372536", ""),
        "Caixa de texto 29": dados_bitrix.get("UF_CRM_1697763267151", ""),
        "Caixa de texto 9": dados_bitrix.get("UF_CRM_1698698407472", ""),
        "Caixa de texto 21": dados_bitrix.get("UF_CRM_1697807340141", ""),
        "Caixa de texto 4": dados_bitrix.get("UF_CRM_1698688252221", ""),
        "Caixa de texto 10": dados_bitrix.get("UF_CRM_1700661252544", ""),
        "Caixa de texto 11": dados_bitrix.get("UF_CRM_1700661287551", ""),
        "Caixa de texto 12": dados_bitrix.get("UF_CRM_1700661275591", ""),
        "Caixa de texto 15": dados_bitrix.get("UF_CRM_1700661314351", ""),
        "Caixa de sele#C3#A7#C3#A3o 1_3": "Yes",
        "Caixa de sele#C3#A7#C3#A3o 2_4": "Yes",
        "Caixa de sele#C3#A7#C3#A3o 3_3": "Yes",
        "Caixa de sele#C3#A7#C3#A3o 4_4": "Yes",
        "Caixa de texto 1_3": formatar_data_para_pdf(
            dados_bitrix.get("UF_CRM_1706040523430", "")
        ),
        "Caixa de texto 1_2": formatar_data_para_pdf(
            dados_bitrix.get("UF_CRM_1706040523430", "")
        ),
    }

    novos_campos_valores = atualizar_valores_com_base_no_status(
        dados_bitrix, novos_campos_valores
    )
    novos_campos_valores = atualizar_campos_com_localizacao(
        dados_bitrix, novos_campos_valores
    )
    novos_campos_valores = atualizar_campos_com_base_no_id(
        dados_bitrix, novos_campos_valores
    )

    # Salva o PDF preenchido
    rename_file_name = dados_bitrix.get("UF_CRM_1697762313423", "Campo não encontrado")
    preencher_campos(pdf_path, novos_campos_valores, rename_file_name)
    pdf_new_path = f"{rename_file_name}" + pdf_path.split("\\")[-1]

    # Comprimir o PDF
    # Comprimir o PDF com Ghostscript
    compressed_pdf_path = pdf_new_path.replace(".pdf", "_compressed.pdf")
    compressed_pdf_path = comprimir_pdf_com_ghostscript(pdf_new_path, compressed_pdf_path)


    encoded_file = file_to_base64(compressed_pdf_path)
    upload_file_to_bitrix(negocio_id, compressed_pdf_path, encoded_file)

    logger.info("PDF processado e comprimido com sucesso.")
    return jsonify({"status": "PDF processado e comprimido com sucesso."})

if __name__ == "__main__":
    app.run(port=6686, host="0.0.0.0")
