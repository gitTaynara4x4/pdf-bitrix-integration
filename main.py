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

# Configuração do Flask
app = Flask(__name__)

# Configuração do Logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Configura o handler para salvar logs em arquivo
file_handler = RotatingFileHandler('app.log', maxBytes=10000000, backupCount=5)
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
CODIGO_BITRIX = os.getenv('CODIGO_BITRIX')
CODIGO_BITRIX_STR = os.getenv('CODIGO_BITRIX_STR')
PROFILE = os.getenv('PROFILE')
BASE_URL_API_BITRIX = os.getenv('BASE_URL_API_BITRIX')

def upload_file_to_bitrix(deal_id, file_name, encoded_file):
    url = f'{BASE_URL_API_BITRIX}/{PROFILE}/{CODIGO_BITRIX}/crm.deal.update'

    fields = {
        'UF_CRM_1723580499': {
            'fileData': [
                file_name,
                encoded_file
            ]
        }
    }

    params = {
        'REGISTER_SONET_EVENT': 'N'
    }

    headers = {
        'Content-Type': 'application/json'
    }

    payload = {
        'id': deal_id,
        'fields': fields,
        'params': params
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get('result'):
            print(f"Deal updated successfully. ID: {data['result']}")
        else:
            print(f"Failed to update deal. Error: {data.get('error')}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to communicate with Bitrix24 API: {e}")

def file_to_base64(file_path):
    with open(file_path, "rb") as file:
        file_data = file.read()
        base64_encoded = base64.b64encode(file_data).decode('utf-8')
        return base64_encoded

def obter_dados_bitrix(campos_ids, negocio_id):
    url = f'{BASE_URL_API_BITRIX}/{PROFILE}/{CODIGO_BITRIX}/crm.deal.get'
    params = {'ID': negocio_id}
    dados_obtidos = {}
    try:
        logger.info(f"Obtendo dados do Bitrix24 para o negócio ID: {negocio_id}")
        resposta = requests.get(url, params=params)
        resposta.raise_for_status()
        dados = resposta.json()
        resultado = dados.get('result', {})
        for campo_id in campos_ids:
            dados_obtidos[campo_id] = resultado.get(campo_id, 'Campo não encontrado')
        logger.info("Dados do Bitrix24 obtidos com sucesso.")
    except requests.RequestException as e:
        logger.error(f"Erro ao obter dados do Bitrix24: {e}")
        for campo_id in campos_ids:
            dados_obtidos[campo_id] = 'Erro'
    return dados_obtidos

def retornar_campos_com_valores(pdf_path):
    logger.info(f"Retornando campos e valores do PDF: {pdf_path}")
    documento = fitz.open(pdf_path)
    campos = {}
    for pagina in documento:
        for widget in pagina.widgets():
            campo_nome = widget.field_name
            campo_tipo = widget.field_type
            campo_valor = widget.field_value if widget.field_value else 'Campo vazio'
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
                logger.debug(f"Atualizando campo '{campo_nome}' de '{widget.field_value}' para '{novo_valor}'")
                widget.field_value = novo_valor
                widget.update()
    novo_pdf_path = f'{name_card}' + pdf_path.split('\\')[-1]
    documento.save(novo_pdf_path)
    documento.close()
    logger.info(f'PDF atualizado salvo em: {novo_pdf_path}')

def formatar_data_para_pdf(data_iso):
    try:
        data_obj = datetime.fromisoformat(data_iso.split('+')[0])
        data_formatada = data_obj.strftime('%d-%m-%Y')
        return data_formatada
    except ValueError:
        logger.error(f"Formato de data inválido: {data_iso}")
        return ''

def separar_data(data_str):
    try:
        data_obj = datetime.strptime(data_str, '%d-%m-%Y')
        dia = data_obj.strftime('%d')
        mes = data_obj.strftime('%m')
        ano = data_obj.strftime('%Y')
        return dia, mes, ano
    except ValueError:
        logger.error(f"Formato de data inválido: {data_str}")
        return '', '', ''

def obter_partes_data(data_str):
    data_formatada = formatar_data_para_pdf(data_str)
    return separar_data(data_formatada)

def atualizar_valores_com_base_no_status(dados_bitrix, novos_campos_valores):
    status = dados_bitrix.get('UF_CRM_1713214941', None)
    if isinstance(status, list):
        status = status[0] if status else ''
    status = str(status).strip()
    logger.debug(f"Valor obtido para UF_CRM_1713214941: '{status}'")
    if status == '48466':
        novos_campos_valores['radio_group_39kkbp'] = 'Value_sgfo'
    elif status == '48468':
        novos_campos_valores['radio_group_41hwgb'] = 'Value_pogq'
    elif status == '48470':
        novos_campos_valores['radio_group_43efsv'] = 'Value_ehsw'
    elif status == '34668':
        novos_campos_valores['radio_group_45jgtf'] = 'Value_uwxo'
    elif status == '48474':
        novos_campos_valores['radio_group_47koeg'] = 'Value_osrb'
    elif status == '48476':
        novos_campos_valores['radio_group_50jafa'] = 'Value_gyvn'
    elif status == '48478':
        novos_campos_valores['radio_group_51djms'] = 'Value_qqsx'
    else:
        logger.warning(f"Status '{status}' não corresponde a nenhum valor conhecido.")
    return novos_campos_valores

def validar_cep(cep):
    cep_limpio = ''.join(c for c in cep if c.isdigit())
    if len(cep_limpio) == 8:
        return cep_limpio
    else:
        logger.warning(f"CEP inválido: {cep}")
        return ''

def obter_cidade_por_cep(cep):
    cep = validar_cep(cep)
    if not cep:
        return ''
    url = f'https://viacep.com.br/ws/{cep}/json/'
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        if 'erro' in dados:
            logger.warning(f"CEP {cep} não encontrado.")
            return ''
        cidade = dados.get('localidade', '')
        return cidade
    except requests.RequestException as e:
        logger.error(f"Erro ao obter cidade para CEP {cep}: {e}")
        return ''

def obter_estado_por_cep(cep):
    cep = validar_cep(cep)
    if not cep:
        return ''
    url = f'https://viacep.com.br/ws/{cep}/json/'
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        if 'erro' in dados:
            logger.warning(f"CEP {cep} não encontrado.")
            return ''
        estado = dados.get('uf', '')
        return estado
    except requests.RequestException as e:
        logger.error(f"Erro ao obter estado para CEP {cep}: {e}")
        return ''

def atualizar_campos_com_localizacao(dados_bitrix, novos_campos_valores):
    cep = dados_bitrix.get('UF_CRM_1700661314351', '')
    cidade = obter_cidade_por_cep(cep)
    estado = obter_estado_por_cep(cep)
    if cidade:
        novos_campos_valores['text_9hsdr'] = cidade
    else:
        novos_campos_valores['text_9hsdr'] = 'CEP não encontrado'
    if estado:
        novos_campos_valores['text_12zlqe'] = estado
    else:
        novos_campos_valores['text_12zlqe'] = 'CEP não encontrado'
    return novos_campos_valores

def atualizar_campos_com_base_no_id(dados_bitrix, novos_campos_valores):
    campo_id = dados_bitrix.get('UF_CRM_1724096872', None)
    if campo_id == '48550':
        novos_campos_valores['radio_group_29bxlm'] = 'Value_wjos'
    elif campo_id == '48548':
        novos_campos_valores['radio_group_30mean'] = 'Value_hocy'
    return novos_campos_valores

@app.route('/processar', methods=['POST'])
def processar():
    negocio_id = request.args.get('negocio_id')
    pdf_path = 'Termo Algar Telecom.pdf'

    if not negocio_id or not pdf_path:
        logger.error('Parâmetros inválidos fornecidos.')
        return jsonify({'erro': 'Parâmetros inválidos.'}), 400

    campos_ids = {
        'UF_CRM_1697762313423': 'Nome',
        'UF_CRM_1723557410': 'Data (dia, mês, ano)',
        'UF_CRM_1697807353336': 'CPF',
        'UF_CRM_1697807372536': 'RG',
        'UF_CRM_1697763267151': 'Nome da mãe',
        'UF_CRM_1698698407472': 'Telefone de contato',
        'UF_CRM_1697807340141': 'Email',
        'UF_CRM_1698688252221': 'Endereço',
        'UF_CRM_1700661252544': 'Número',
        'UF_CRM_1700661287551': 'Bairro',
        'UF_CRM_1700661275591': 'Complemento',
        'UF_CRM_1709042046': 'Cidade',
        'UF_CRM_1700661314351': 'CEP',
        'UF_CRM_1713214941': 'Status',
        'UF_CRM_1706040523430': 'Data da Venda',
        'OPPORTUNITY': 'Valor e Moeda',
        'UF_CRM_1724096872': 'ID do campo adicional'
    }
    
    dados_bitrix = obter_dados_bitrix(campos_ids.keys(), negocio_id)
    data_str = dados_bitrix.get('UF_CRM_1723557410', '')
    dia, mes, ano = obter_partes_data(data_str)

    novos_campos_valores = {
        'text_6evpi': dados_bitrix.get('UF_CRM_1697807340141', ''),
        'text_79rqsc': dados_bitrix.get('OPPORTUNITY', ''),
        'text_1gooi': dados_bitrix.get('UF_CRM_1697762313423', 'Campo não encontrado'),
        'text_18fs': dia,
        'text_19yfhh': mes,
        'text_17hemi': ano,
        'text_37fevi': dados_bitrix.get('UF_CRM_1697807353336', ''),
        'text_15fczk': dados_bitrix.get('UF_CRM_1697807372536', ''),
        'text_4iutf': dados_bitrix.get('UF_CRM_1697763267151', ''),
        'text_11cqnn': dados_bitrix.get('UF_CRM_1698698407472', ''),
        'text_5ilyx': dados_bitrix.get('UF_CRM_1697807340141', ''),
        'text_2wlhk': dados_bitrix.get('UF_CRM_1698688252221', ''),
        'text_14wobm': dados_bitrix.get('UF_CRM_1700661252544', ''),
        'text_13uzhe': dados_bitrix.get('UF_CRM_1700661287551', ''),
        'text_8acen': dados_bitrix.get('UF_CRM_1700661275591', ''),
        'text_9hsdr': '',
        'text_10dapr': dados_bitrix.get('UF_CRM_1700661314351', ''),
        'text_12zlqe': '',
        'radio_group_36ssax': 'Value_kjhe',
        'radio_group_52updr': 'Value_zeqg',
        'radio_group_57tgeo': 'Value_vxqb',
        'radio_group_62waaf': 'Value_pjxm',
        'radio_group_75tpzp': 'Value_huvw',
        'radio_group_77vgzg': 'Value_rjkp',
        'radio_group_78rsrq': 'Value_mfo',
        'radio_group_86tbnz': 'Value_abgf',
        'radio_group_88ustu': 'Value_lirc',
        'radio_group_89dttg': 'Value_neml',
        'radio_group_91molt': 'Value_pkjn',
        'text_90pciz': formatar_data_para_pdf(dados_bitrix.get('UF_CRM_1706040523430', '')),
        'text_92ejfl': formatar_data_para_pdf(dados_bitrix.get('UF_CRM_1706040523430', ''))
    }
    
    novos_campos_valores = atualizar_valores_com_base_no_status(dados_bitrix, novos_campos_valores)
    novos_campos_valores = atualizar_campos_com_localizacao(dados_bitrix, novos_campos_valores)
    novos_campos_valores = atualizar_campos_com_base_no_id(dados_bitrix, novos_campos_valores)

    # Salva o PDF preenchido
    rename_file_name = dados_bitrix.get('UF_CRM_1697762313423', 'Campo não encontrado')
    preencher_campos(pdf_path, novos_campos_valores, rename_file_name)
    pdf_new_path = f'{rename_file_name}' + pdf_path.split('\\')[-1]
    encoded_file = file_to_base64(pdf_new_path)
    upload_file_to_bitrix(negocio_id, pdf_new_path, encoded_file)

    logger.info('PDF processado com sucesso.')
    return jsonify({'status': 'PDF processado com sucesso.'})

if __name__ == "__main__":
    app.run(port=6686, host ='0.0.0.0')
