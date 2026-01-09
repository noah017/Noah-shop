import os
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import psycopg2

# Carrega a URL do banco do arquivo .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = Flask(__name__)

# --- FUNÇÕES DO BANCO DE DADOS ---

def get_db_connection():
    """Cria e retorna a conexão com o Supabase/PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        # Em produção (Vercel), se a conexão falhar, o app não inicia.
        # Aqui, apenas printamos o erro no console do Termux.
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def criar_tabela_se_nao_existir():
    """Garante que a tabela 'pedidos' exista com as colunas corretas."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                produto TEXT NOT NULL,
                valor NUMERIC(10, 2) NOT NULL,
                nome TEXT NOT NULL,
                telefone TEXT,
                cep TEXT,
                endereco TEXT,
                cidade_estado TEXT,
                status TEXT DEFAULT 'AGUARDANDO PAGAMENTO'
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()

# Executa a função para garantir que o banco esteja pronto
criar_tabela_se_nao_existir() 


# --- ROTAS DA LOJA E ADMIN (Lógica de Venda) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/checkout')
def checkout():
    contato_comprovante = "16997200593"
    return render_template('checkout.html', contato_comprovante=contato_comprovante)

@app.route('/comprar', methods=['POST'])
def comprar():
    conn = get_db_connection()
    if not conn:
        return "Erro (500): Conexão com o banco falhou.", 500

    produto = request.form.get('produtoNome').replace('+', ' ')
    valor = request.form.get('valorTotal')
    nome = request.form.get('nome')
    telefone = request.form.get('telefone')
    cep = request.form.get('cep')
    
    # Combina campos de endereço
    endereco = f"{request.form.get('logradouro')}, Nº {request.form.get('numero')} - {request.form.get('bairro')}"
    cidade_estado = f"{request.form.get('cidade')}/{request.form.get('estado')}"

    try:
        cursor = conn.cursor()
        # Insere o pedido no Banco de Dados Supabase
        cursor.execute("""
            INSERT INTO pedidos (produto, valor, nome, telefone, cep, endereco, cidade_estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """, (produto, valor, nome, telefone, cep, endereco, cidade_estado))
        
        # Pega o ID que acabou de ser criado (necessário para a confirmação)
        pedido_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return redirect(url_for('confirmacao_pix', pedido_id=pedido_id)) 

    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar pedido: {e}")
        return "Erro ao finalizar pedido.", 500

@app.route('/confirmacao_pix/<int:pedido_id>')
def confirmacao_pix(pedido_id):
    conn = get_db_connection()
    if not conn:
        return "Erro (500): Conexão com o banco falhou.", 500
        
    cursor = conn.cursor()
    cursor.execute("SELECT produto, valor FROM pedidos WHERE id = %s", (pedido_id,))
    pedido_db = cursor.fetchone()
    cursor.close()
    conn.close()

    if pedido_db is None:
        return redirect(url_for('index'))

    # Formata os dados para o template
    pedido = {'produto': pedido_db[0], 'valor': pedido_db[1]}
    chave_pix = "16997200593"
    contato_comprovante = chave_pix
    
    return render_template('confirmacao.html', pedido=pedido, chave_pix=chave_pix, contato_comprovante=contato_comprovante)


# --- ROTAS DO ADMIN (Persistente) ---

@app.route('/admin')
def admin_panel():
    conn = get_db_connection()
    if not conn:
        return "Erro (500): Conexão com o banco falhou.", 500
        
    cursor = conn.cursor()
    # Busca todos os pedidos do Supabase (ordenados do mais novo para o mais antigo)
    cursor.execute("SELECT id, produto, valor, nome, telefone, endereco, cidade_estado, status FROM pedidos ORDER BY id DESC")
    pedidos_db = cursor.fetchall() 
    cursor.close()
    conn.close()

    pedidos = []
    for row in pedidos_db:
        pedidos.append({
            'id': row[0],
            'produto': row[1],
            'valor': row[2],
            'nome': row[3],
            'telefone': row[4],
            'endereco': row[5],
            'cidade_estado': row[6],
            'status': row[7]
        })
        
    return render_template('admin.html', pedidos=pedidos)

@app.route('/admin/confirmar/<int:pedido_id>')
def confirmar_pagamento(pedido_id):
    conn = get_db_connection()
    if not conn:
        return "Erro (500): Conexão com o banco falhou.", 500
        
    cursor = conn.cursor()
    # ATUALIZA o status no Supabase
    cursor.execute("UPDATE pedidos SET status = 'PAGAMENTO CONFIRMADO' WHERE id = %s", (pedido_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/deletar/<int:pedido_id>')
def deletar_pedido(pedido_id):
    conn = get_db_connection()
    if not conn:
        return "Erro (500): Conexão com o banco falhou.", 500

    cursor = conn.cursor()
    # DELETA o pedido do Supabase
    cursor.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_panel'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
