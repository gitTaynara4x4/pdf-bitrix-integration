from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Mapeamento dos IDs para os nomes
responsaveis = {
    "148": "Geovanna Emanuelly",
    "154": "Gustavo Inácio",
    "158": "Felipe Marchezine",
    "34874": "Taynara Francine",
    "43180": "Sabrina Emanuelle",
    "48604": "Ian Henrique",
    "48618": "Tiago Martins",
    "48674": "Caio Sales",
    "49718": "Italo Almeida",
    "48678": "Jéssica Hellen",
    "49722": "Laisa Reis",
    "34794": "Treinamento 01",
    "48596": "Treinamento 02",
    "48610": "Treinamento 03",
    "48612": "Treinamento 04"
}

# Webhook do Bitrix24
webhook_url = "https://marketingsolucoes.bitrix24.com.br/rest/35002/7a2nuej815yjx5bg/"

# Função para buscar o nome do responsável baseado no ID
def get_user_name_by_id(user_id):
    # Retorna o nome correspondente ao ID, ou None se não encontrar
    return responsaveis.get(user_id, None)

# Função para atualizar o card no Bitrix24
def update_deal(deal_id, value):
    url = f"{webhook_url}crm.deal.update.json"
    data = {
        "ID": deal_id,
        "FIELDS": {
            "UF_CRM_1732282217": value  # Atualiza o campo desejado no card
        }
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return {"status": "success", "message": f"Card {deal_id} atualizado com sucesso!"}
    else:
        return {"status": "error", "message": f"Erro ao atualizar o card {deal_id}: {response.status_code}"}

# Função para processar e atualizar o card
def process_card_update(deal_id, responsavel_id):
    # Busca o nome do responsável usando o ID
    responsavel_nome = get_user_name_by_id(responsavel_id)
    if responsavel_nome:
        # Atualiza o campo do card com o nome do responsável
        return update_deal(deal_id, responsavel_nome)
    else:
        return {"status": "error", "message": "ID do responsável não encontrado."}

# Endpoint da API que recebe o ID do card e o ID do responsável
@app.route('/update_card', methods=['GET'])
def update_card():
    # Receber os parâmetros da URL
    deal_id = request.args.get('deal_id')
    responsavel_id = request.args.get('responsavel_id')

    # Validar os parâmetros
    if not deal_id or not responsavel_id:
        return jsonify({"status": "error", "message": "Parâmetros 'deal_id' e 'responsavel_id' são obrigatórios."}), 400

    # Processar e atualizar o card
    result = process_card_update(deal_id, responsavel_id)
    return jsonify(result), 200

# Rodar o servidor Flask
if __name__ == '__main__':
    app.run(debug=True, port=8858)
