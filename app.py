import os
import time
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# --- Funções de Manipulação de Arquivo (Substitui o Banco de Dados) ---

def get_pedidos():
    """Lê os pedidos do arquivo db.txt e retorna uma lista de dicionários."""
    try:
        # Abre o arquivo em modo de leitura 'r'
        # O encoding='utf-8' é importante para caracteres especiais
        with open('db.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        pedidos = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # O formato é: ID||Nome||Email||Produto||Valor||Data
            # Usamos '||' como separador para evitar problemas com vírgulas ou nomes
            parts = line.split('||') 
            
            if len(parts) >= 6:
                pedidos.append({
                    'id': parts[0],
                    'nome': parts[1],
                    'email': parts[2],
                    'produto': parts[3],
                    'valor': parts[4],
                    'data': parts[5] 
                })
        return pedidos
        
    except FileNotFoundError:
        # Retorna lista vazia se o arquivo db.txt ainda não existe
        return []
    except Exception as e:
        print(f"Erro ao ler db.txt: {e}")
        return []


def salvar_pedido(nome, email, produto, valor):
    """Anexa um novo pedido no final do arquivo db.txt."""
    try:
        # Cria um ID único baseado no tempo em milissegundos
        pedido_id = int(time.time() * 1000) 
        
        # Formata a data e hora atual
        data_pedido = time.strftime("%Y-%m-%d %H:%M:%S")

        # Monta a linha do pedido (separador '||')
        pedido_line = f"{pedido_id}||{nome}||{email}||{produto}||{valor}||{data_pedido}\n"

        # Abre o arquivo em modo de anexar 'a' (append)
        with open('db.txt', 'a', encoding='utf-8') as f:
            f.write(pedido_line)
            
        return True
    except Exception as e:
        print(f"Erro ao salvar no db.txt: {e}")
        return False

# ------------------------------------------------------------------------


# --- Rotas do Aplicativo ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/comprar", methods=["POST"])
def comprar():
    # Coleta os dados do formulário
    nome = request.form.get("nome")
    email = request.form.get("email")
    produto = request.form.get("produto")
    valor = request.form.get("valor")

    # Chama a função que salva no arquivo db.txt
    if salvar_pedido(nome, email, produto, valor):
        return render_template("confirmacao_pix.html", nome=nome, produto=produto, valor=valor)
    else:
        # Em caso de falha no salvamento do arquivo (raro)
        return "Erro interno ao processar o pedido.", 500

@app.route("/admin")
def admin():
    # Chama a função que lê do arquivo db.txt
    pedidos = get_pedidos()
    # A tabela no admin.html irá renderizar estes pedidos
    return render_template("admin.html", pedidos=pedidos)

@app.errorhandler(500)
def internal_error(error):
    # Opcional: Para debugar, você pode retornar a mensagem de erro real
    # Mas para o usuário, é melhor uma mensagem simples.
    # return "Ocorreu um erro interno no servidor.", 500 
    return render_template("500.html"), 500 

if __name__ == "__main__":
    # Em ambiente de produção (Vercel), o servidor Gunicorn irá rodar o app
    # Em ambiente de desenvolvimento local, você pode usar:
    # app.run(debug=True)
    pass
