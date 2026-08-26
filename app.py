from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "chave_secreta_total_techstore"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estoque.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ================= MODELOS DO BANCO DE DADOS =================
class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    imagem = db.Column(db.String(100), nullable=False)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    nome_cliente = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    cep = db.Column(db.String(20), nullable=False)
    pagamento = db.Column(db.String(50), nullable=False)
    total = db.Column(db.Float, nullable=False)
    itens_resumo = db.Column(db.String(500), nullable=False)

class Avaliacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    usuario_nome = db.Column(db.String(100), nullable=False)
    nota = db.Column(db.Integer, nullable=False)
    comentario = db.Column(db.Text, nullable=False)


# ================= ROTAS DE NAVEGAÇÃO E VITRINE =================
@app.route("/")
def home():
    categoria_selecionada = request.args.get('categoria')
    termo_busca = request.args.get('busca', '').strip()
    
    query = Produto.query
    if categoria_selecionada:
        query = query.filter_by(categoria=categoria_selecionada)
    if termo_busca:
        query = query.filter(Produto.nome.ilike(f"%{termo_busca}%"))

    produtos = query.all()
    qtd_carrinho = sum(session.get('carrinho', {}).values())
    return render_template("index.html", estoque=produtos, qtd_carrinho=qtd_carrinho, categoria_atual=categoria_selecionada, termo_busca=termo_busca)


@app.route("/produto/<int:produto_id>")
def detalhes_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    avaliacoes = Avaliacao.query.filter_by(produto_id=produto_id).all()
    qtd_carrinho = sum(session.get('carrinho', {}).values())
    return render_template("detalhes.html", produto=produto, avaliacoes=avaliacoes, qtd_carrinho=qtd_carrinho)


@app.route("/produto/<int:produto_id>/avaliar", methods=["POST"])
def avaliar_produto(produto_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    nota = int(request.form.get("nota"))
    comentario = request.form.get("comentario")
    usuario_nome = session.get('usuario_nome', 'Cliente')

    nova_avaliacao = Avaliacao(produto_id=produto_id, usuario_nome=usuario_nome, nota=nota, comentario=comentario)
    db.session.add(nova_avaliacao)
    db.session.commit()
    return redirect(url_for('detalhes_produto', produto_id=produto_id))


# ================= ROTAS DE CARRINHO E COMPRAS =================
@app.route("/adicionar/<int:produto_id>", methods=["POST"])
def adicionar_carrinho(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    if 'carrinho' not in session:
        session['carrinho'] = {}
    carrinho = session['carrinho']
    id_str = str(produto_id)
    if carrinho.get(id_str, 0) + 1 <= produto.quantidade:
        carrinho[id_str] = carrinho.get(id_str, 0) + 1
        session.modified = True
    return redirect(url_for('home'))


@app.route("/comprar-direto/<int:produto_id>", methods=["POST"])
def comprar_direto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    if 'carrinho' not in session:
        session['carrinho'] = {}
    carrinho = session['carrinho']
    id_str = str(produto_id)
    if carrinho.get(id_str, 0) + 1 <= produto.quantidade:
        carrinho[id_str] = carrinho.get(id_str, 0) + 1
        session.modified = True
    return redirect(url_for('ver_carrinho'))


@app.route("/carrinho")
def ver_carrinho():
    if 'carrinho' not in session or not session['carrinho']:
        return render_template("carrinho.html", itens=[], total=0, frete=0)
    
    carrinho = session['carrinho']
    itens_carrinho = []
    total = 0

    for id_str, qtd in carrinho.items():
        produto = Produto.query.get(int(id_str))
        if produto:
            subtotal = produto.preco * qtd
            total += subtotal
            itens_carrinho.append({'produto': produto, 'quantidade': qtd, 'subtotal': subtotal})
    
    # Frete fixo base
    frete = 25.00 if total > 0 else 0
    return render_template("carrinho.html", itens=itens_carrinho, total=total, frete=frete)


@app.route("/remover-carrinho/<int:produto_id>", methods=["POST"])
def remover_carrinho(produto_id):
    if 'carrinho' in session:
        id_str = str(produto_id)
        if id_str in session['carrinho']:
            del session['carrinho'][id_str]
            session.modified = True
    return redirect(url_for('ver_carrinho'))


@app.route("/calcular-frete", methods=["POST"])
def calcular_frete():
    cep = request.form.get("cep", "").strip().replace("-", "")
    # Regra simples: CEPs começando com '0' (ex: Grande São Paulo) pagam frete menor
    if cep.startswith('0'):
        valor_frete = 15.00
    else:
        valor_frete = 35.00
    session['frete_valor'] = valor_frete
    return redirect(url_for('ver_carrinho'))


@app.route("/finalizar", methods=["POST"])
def finalizar_compra():
    if 'carrinho' in session and session['carrinho']:
        carrinho = session['carrinho']
        total_produtos = 0
        resumo_itens = []

        for id_str, qtd in carrinho.items():
            produto = Produto.query.get(int(id_str))
            if produto and produto.quantidade >= qtd:
                produto.quantidade -= qtd
                total_produtos += produto.preco * qtd
                resumo_itens.append(f"{qtd}x {produto.nome}")

        frete = session.get('frete_valor', 25.00)
        total_geral = total_produtos + frete

        novo_pedido = Pedido(
            usuario_id=session.get('usuario_id'),
            nome_cliente=session.get('usuario_nome', 'Cliente Convidado'),
            telefone='Não informado',
            cep='00000-000',
            pagamento='Cartão/PIX',
            total=total_geral,
            itens_resumo=", ".join(resumo_itens)
        )
        db.session.add(novo_pedido)
        db.session.commit()
        session.pop('carrinho', None)
        session.pop('frete_valor', None)

    return redirect(url_for('meus_pedidos'))


@app.route("/comprar-formulario/<int:produto_id>", methods=["POST"])
def comprar_formulario(produto_id):
    nome_cliente = request.form.get("nome")
    telefone = request.form.get("telefone")
    cep = request.form.get("cep")
    pagamento = request.form.get("pagamento")
    
    produto = Produto.query.get_or_404(produto_id)
    if produto.quantidade > 0:
        produto.quantidade -= 1
        
        # Calcular frete unitário baseado no CEP
        frete = 15.00 if cep.startswith('0') else 30.00
        total_geral = produto.preco + frete

        novo_pedido = Pedido(
            usuario_id=session.get('usuario_id'),
            nome_cliente=nome_cliente,
            telefone=telefone,
            cep=cep,
            pagamento=pagamento,
            total=total_geral,
            itens_resumo=f"1x {produto.nome}"
        )
        db.session.add(novo_pedido)
        db.session.commit()

    return render_template("sucesso.html", nome=nome_cliente, produto=produto, pagamento=pagamento, total=total_geral, frete=frete)


@app.route("/comprovante/<int:pedido_id>")
def gerar_comprovante_pdf(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setTitle(f"Comprovante_Pedido_{pedido.id}")

    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, 750, "TechStore - Comprovante de Pedido")

    p.setFont("Helvetica", 12)
    p.drawString(50, 710, f"Número do Pedido: #{pedido.id}")
    p.drawString(50, 690, f"Cliente: {pedido.nome_cliente}")
    p.drawString(50, 670, f"Telefone: {pedido.telefone}")
    p.drawString(50, 650, f"CEP de Destino: {pedido.cep}")
    p.drawString(50, 630, f"Forma de Pagamento: {pedido.pagamento}")
    
    p.drawString(50, 590, f"Itens: {pedido.itens_resumo}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 550, f"Valor Total Pago: R$ {pedido.total:.2f}")

    p.showPage()
    p.save()
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"comprovante_pedido_{pedido.id}.pdf", mimetype='application/pdf')


@app.route("/meus-pedidos")
def meus_pedidos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    pedidos = Pedido.query.filter_by(usuario_id=session['usuario_id']).all()
    return render_template("pedidos.html", pedidos=pedidos)


# ================= AUTENTICAÇÃO E ADMIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")
        
        usuario = Usuario.query.filter_by(email=email, senha=senha).first()
        if usuario:
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            session['eh_admin'] = usuario.is_admin
            
            if usuario.is_admin:
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('home'))
        else:
            return render_template("login.html", erro="E-mail ou senha incorretos!")
            
    return render_template("login.html", erro=None)


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")

        if Usuario.query.filter_by(email=email).first():
            return render_template("registro.html", erro="Este e-mail já está cadastrado.")

        novo_usuario = Usuario(nome=nome, email=email, senha=senha, is_admin=False)
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template("registro.html", erro=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route("/admin")
def admin():
    if not session.get('eh_admin'):
        return redirect(url_for('login'))
    produtos = Produto.query.all()
    return render_template("admin.html", estoque=produtos)


@app.route("/admin/cadastrar", methods=["POST"])
def cadastrar_produto():
    if not session.get('eh_admin'):
        return redirect(url_for('login'))
        
    nome = request.form.get("nome")
    categoria = request.form.get("categoria")
    preco = float(request.form.get("preco"))
    quantidade = int(request.form.get("quantidade"))
    imagem = request.form.get("imagem")

    novo_produto = Produto(nome=nome, categoria=categoria, preco=preco, quantidade=quantidade, imagem=imagem)
    db.session.add(novo_produto)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route("/admin/remover/<int:produto_id>", methods=["POST"])
def remover_produto(produto_id):
    if not session.get('eh_admin'):
        return redirect(url_for('login'))
        
    produto = Produto.query.get_or_404(produto_id)
    db.session.delete(produto)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route("/atualizar", methods=["POST"])
def atualizar():
    if not session.get('eh_admin'):
        return redirect(url_for('login'))
        
    produto_id = request.form.get("codigo")
    operacao = request.form.get("operacao")
    quantidade_str = request.form.get("quantidade")
    try:
        quantidade = int(quantidade_str)
        produto = Produto.query.get(produto_id)
        if produto and quantidade > 0:
            if operacao == "entrada":
                produto.quantidade += quantidade
            elif operacao == "saida":
                if quantidade <= produto.quantidade:
                    produto.quantidade -= quantidade
            db.session.commit()
    except ValueError:
        pass 
    return redirect(url_for("admin"))


@app.route("/api/qtd-carrinho")
def api_qtd_carrinho():
    total = sum(session.get('carrinho', {}).values())
    return {"total": total}


# Inicialização com Admin padrão e produtos iniciais
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(email="admin@techstore.com").first():
        admin_user = Usuario(nome="Administrador", email="admin@techstore.com", senha="admin123", is_admin=True)
        db.session.add(admin_user)
        db.session.commit()

    if not Produto.query.first():
        p1 = Produto(nome="Teclado Aula WIN60HE MAX (Preto)", categoria="Periféricos", preco=850.0, quantidade=10, imagem="teclado.jpg")
        p2 = Produto(nome="Processador AMD Ryzen 7 7700X", categoria="Hardware", preco=2300.0, quantidade=5, imagem="processador.jpg")
        p3 = Produto(nome="Placa-Mãe Gigabyte B650", categoria="Hardware", preco=1450.0, quantidade=8, imagem="placamae.jpg")
        db.session.add_all([p1, p2, p3])
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)