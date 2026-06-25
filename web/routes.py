"""
Rotas do SGM - Sistema de Gerenciamento de Mercearia

Organização:
1. Decoradores de segurança (require_login, require_admin)
2. Autenticação (login, logout)
3. Dashboard principal
4. API para busca de clientes
5. CRUD de Clientes
6. CRUD de Usuários (Admin)
7. Gestão Financeira (Dívidas, Pagamentos, Renegociações)
8. Relatórios
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from web.models import db, Cliente, Usuario, Divida, Pagamento, Renegociacao, Parcela
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from werkzeug.security import check_password_hash, generate_password_hash
from collections import defaultdict
import calendar


def register_routes(app):
    """Registra todas as rotas da aplicação"""
    bp = Blueprint('main', __name__)

    # ==================== DECORADORES DE SEGURANÇA ====================
    
    def require_login(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('main.login'))
            return fn(*args, **kwargs)
        return wrapper

    def require_admin(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('main.login'))
            if session.get('user_tipo') != 'Administrador':
                flash('Acesso negado: apenas administradores.')
                return redirect(url_for('main.home'))
            return fn(*args, **kwargs)
        return wrapper

    # ==================== AUTENTICAÇÃO ====================
    @bp.route('/', methods=['GET', 'POST'])
    def login():
        """Página de login do sistema"""
        if request.method == 'POST':
            usuario = request.form.get('usuario')
            senha = request.form.get('senha')

            # Busca usuário por nome ou email
            user = Usuario.query.filter(
                (Usuario.nome == usuario) | (Usuario.email == usuario)
            ).first()
            
            # Valida senha
            if user and check_password_hash(user.senha_hash, senha or ''):
                # Salva dados na sessão
                session['user_id'] = user.id
                session['user_nome'] = user.nome
                session['user_tipo'] = user.tipo
                return redirect(url_for('main.home'))
            
            flash('Credenciais inválidas')
        
        return render_template('login.html')

    @bp.route('/logout')
    def logout():
        """Faz logout limpando a sessão"""
        session.clear()
        return redirect(url_for('main.login'))

    # ==================== DASHBOARD PRINCIPAL ====================
    @bp.route('/home')
    @require_login
    def home():
        """
        Dashboard principal
        - Admin: exibe dashboard completo com KPIs e gráficos
        - Caixa: tela básica para operações
        """
        tipo = session.get('user_tipo')
        
        # Se vier com cliente_id, renderiza página vazia para o JavaScript preencher
        if request.args.get('cliente_id'):
            return render_template('home.html', dashboard=False, hide_aside=False)
        
        if tipo == 'Administrador':
            # Carrega todos os dados necessários
            dividas = Divida.query.all()
            pagamentos = Pagamento.query.all()
            hoje = date.today()

            # ===== KPIs (Indicadores) =====
            total_a_receber = sum(d.saldo_devedor for d in dividas if d.status != 'Paga')
            total_vencido = sum(
                d.saldo_devedor for d in dividas 
                if d.status != 'Paga' and d.data_vencimento <= hoje
            )
            qtd_pagas = sum(1 for d in dividas if d.status == 'Paga')
            qtd_vencidas = sum(1 for d in dividas if d.status != 'Paga' and d.data_vencimento < hoje)
            qtd_abertas = sum(1 for d in dividas if d.status != 'Paga' and d.data_vencimento >= hoje)

            # ===== Ranking: Top 5 devedores =====
            ranking = {}
            for d in dividas:
                if d.status == 'Paga':
                    continue
                nome = d.cliente.nome
                ranking[nome] = ranking.get(nome, 0) + d.saldo_devedor
            
            ranking_ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)[:5]
            top_labels = [n for n, _ in ranking_ordenado]
            top_values = [v for _, v in ranking_ordenado]

            # ===== Contagem por Status =====
            pagas_ct = 0
            renegociadas_ct = 0
            vencidas_ct = 0
            em_dia_ct = 0
            
            for d in dividas:
                if d.status == 'Paga' or d.saldo_devedor <= 0:
                    pagas_ct += 1
                elif d.data_vencimento <= hoje and d.saldo_devedor > 0:
                    # Vencida tem prioridade sobre status (inclui hoje)
                    vencidas_ct += 1
                elif d.status == 'Renegociada' and d.saldo_devedor > 0:
                    renegociadas_ct += 1
                elif d.saldo_devedor > 0:
                    em_dia_ct += 1

            # ===== Pagamentos por Meio =====
            meio_map = {}
            for p in pagamentos:
                meio = p.meio_pagamento or 'Outro'
                meio_map[meio] = meio_map.get(meio, 0) + 1
            meio_labels = list(meio_map.keys())
            meio_values = list(meio_map.values())

            # ===== Dívidas por Mês (últimos 6 meses) =====
            by_month = defaultdict(float)
            for d in dividas:
                if d.data_venda:
                    ano, mes = d.data_venda.year, d.data_venda.month
                    by_month[(ano, mes)] += float(d.valor_original or 0)
            
            # Monta labels e valores dos últimos 6 meses
            labels_month = []
            values_month = []
            ref = date(hoje.year, hoje.month, 1)
            
            for i in range(5, -1, -1):
                ano = ref.year
                mes = ref.month - i
                # Ajusta ano se mês for negativo
                while mes <= 0:
                    ano -= 1
                    mes += 12
                
                labels_month.append(f"{calendar.month_abbr[mes]}/{str(ano)[-2:]}")
                values_month.append(round(by_month.get((ano, mes), 0.0), 2))

            # ===== Lista de Dívidas Vencidas =====
            dividas_vencidas = []
            for d in dividas:
                if d.status != 'Paga' and d.saldo_devedor > 0 and d.data_vencimento <= hoje:
                    dividas_vencidas.append({
                        'id': d.id,
                        'cliente_nome': d.cliente.nome,
                        'descricao': d.descricao or 'Sem descrição',
                        'saldo': d.saldo_devedor,
                        'vencimento': d.data_vencimento
                    })
            # Ordenar por vencimento (mais antigas primeiro)
            dividas_vencidas.sort(key=lambda x: x['vencimento'])

            return render_template(
                'home.html',
                dashboard=True,
                total_a_receber=total_a_receber,
                total_vencido=total_vencido,
                qtd_pagas=qtd_pagas,
                qtd_vencidas=qtd_vencidas,
                qtd_abertas=qtd_abertas,
                ranking=ranking_ordenado,
                dividas_vencidas=dividas_vencidas,
                # dados para gráficos
                top_labels=top_labels,
                top_values=top_values,
                status_labels=['Pagas', 'Em dia', 'Renegociadas', 'Vencidas'],
                status_values=[pagas_ct, em_dia_ct, renegociadas_ct, vencidas_ct],
                meio_labels=meio_labels,
                meio_values=meio_values,
                month_labels=labels_month,
                month_values=values_month,
            )

        # Caixa: tela simples sem dashboard
        return render_template('home.html', dashboard=False)

    # ==================== API - HEALTH CHECK ====================

    @bp.route('/api/health')
    def api_health():
        try:
            db.session.execute(db.text('SELECT 1'))
            return jsonify({'status': 'operational'}), 200
        except Exception as e:
            return jsonify({'status': 'outage', 'detail': str(e)}), 503

    # ==================== API - BUSCA DE CLIENTES ====================
    
    @bp.route('/api/clientes')
    @require_login
    def api_clientes():
        """
        Lista clientes cadastrados
        ---
        summary: Lista clientes
        tags:
          - Clientes
        parameters:
          - name: q
            in: query
            type: string
            required: false
            description: Filtro parcial por nome do cliente
        responses:
          200:
            description: Lista de clientes
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  nome:
                    type: string
                    example: "João Silva"
        """
        q = request.args.get('q', '').strip()

        if q:
            clientes = Cliente.query.filter(Cliente.nome.ilike(f'%{q}%')).all()
        else:
            clientes = Cliente.query.order_by(Cliente.nome).all()

        result = [{'id': c.id, 'nome': c.nome} for c in clientes]
        return jsonify(result)

    @bp.route('/api/cliente/<int:cliente_id>')
    @require_login
    def api_cliente(cliente_id):
        """
        Dados completos de um cliente
        ---
        summary: Buscar cliente por ID
        tags:
          - Clientes
        parameters:
          - name: cliente_id
            in: path
            type: integer
            required: true
            description: ID do cliente
        responses:
          200:
            description: Dados do cliente com dívidas, pagamentos e parcelas
            schema:
              type: object
              properties:
                id:
                  type: integer
                nome:
                  type: string
                cpf:
                  type: string
                celular:
                  type: string
                endereco:
                  type: string
                nivel:
                  type: string
                  enum: [Novo, Bronze, Prata, Ouro]
                limite:
                  type: number
                dividas:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: integer
                      valor_original:
                        type: number
                      saldo:
                        type: number
                      vencimento:
                        type: string
                        format: date
                      status:
                        type: string
                        enum: [Pendente, Paga, Renegociada]
                      descricao:
                        type: string
                      parcelado:
                        type: boolean
                      num_parcelas:
                        type: integer
                      juros_parcelamento:
                        type: number
                      pagamentos:
                        type: array
                        items:
                          type: object
                      renegociacoes:
                        type: array
                        items:
                          type: object
                      parcelas:
                        type: array
                        items:
                          type: object
          404:
            description: Cliente não encontrado
        """
        c = Cliente.query.get_or_404(cliente_id)
        
        # Monta lista de dívidas com pagamentos e renegociações
        dividas = []
        for d in c.dividas:
            pagamentos = [
                {
                    'id': p.id,
                    'valor': p.valor,
                    'data': p.data_pagamento.isoformat(),
                    'meio': p.meio_pagamento
                }
                for p in d.pagamentos
            ]
            
            reneg = [
                {
                    'id': r.id,
                    'nova_data_venc': r.nova_data_venc.isoformat(),
                    'juros': r.juros_percent,
                    'data': r.data_reneg.isoformat()
                }
                for r in d.renegociacoes
            ]
            
            parcelas = [
                {
                    'numero': p.numero_parcela,
                    'valor_parcela': p.valor_parcela,
                    'data_vencimento': p.data_vencimento.isoformat(),
                    'status': p.status,
                    'valor_pago': p.valor_pago
                }
                for p in d.parcelas
            ]
            
            dividas.append({
                'id': d.id,
                'valor_original': d.valor_original,
                'saldo': d.saldo_devedor,
                'vencimento': d.data_vencimento.isoformat(),
                'status': d.status,
                'descricao': d.descricao,
                'parcelado': d.parcelado,
                'num_parcelas': d.num_parcelas,
                'juros_parcelamento': d.juros_parcelamento,
                'pagamentos': pagamentos,
                'renegociacoes': reneg,
                'parcelas': parcelas
            })

        # Monta resposta completa
        data = {
            'id': c.id,
            'nome': c.nome,
            'cpf': c.cpf,
            'celular': c.celular,
            'endereco': c.endereco,
            'nivel': c.nivel_confianca,
            'limite': c.limite_credito,
            'dividas': dividas
        }
        return jsonify(data)

    # ==================== CRUD - CLIENTES ====================
    @bp.route('/clientes')
    @require_login
    def listar_clientes():
        """Lista todos os clientes cadastrados"""
        clientes = Cliente.query.order_by(Cliente.nome).all()
        return render_template('clientes_list.html', clientes=clientes)

    @bp.route('/clientes/novo', methods=['GET', 'POST'])
    @require_login
    def novo_cliente():
        """Cadastro de novo cliente"""
        if request.method == 'POST':
            nome = request.form.get('nome')
            cpf = request.form.get('cpf')
            celular = request.form.get('celular')
            endereco = request.form.get('endereco')
            nivel = request.form.get('nivel') or 'Novo'
            limite = float(request.form.get('limite') or 200.0)

            # Valida se cliente já existe
            if Cliente.query.filter_by(nome=nome).first():
                flash('Erro: Já existe um cliente cadastrado com este nome.')
                return render_template('clientes_form.html')

            # Cria e salva novo cliente
            cliente = Cliente(
                nome=nome,
                cpf=cpf,
                celular=celular,
                endereco=endereco,
                nivel_confianca=nivel,
                limite_credito=limite
            )
            db.session.add(cliente)
            db.session.commit()
            
            flash('Cliente cadastrado com sucesso.')
            return redirect(url_for('main.home') + f'?cliente_id={cliente.id}')

        return render_template('clientes_form.html')

    @bp.route('/clientes/<int:cliente_id>/apagar', methods=['POST'])
    @require_admin
    def apagar_cliente(cliente_id):
        """Apaga cliente e todos os dados associados (apenas admin)"""
        cliente = Cliente.query.get_or_404(cliente_id)
        
        # Cascade delete já configurado no modelo, mas fazendo manualmente por garantia
        dividas = Divida.query.filter_by(cliente_id=cliente.id).all()
        for d in dividas:
            Pagamento.query.filter_by(divida_id=d.id).delete()
            Renegociacao.query.filter_by(divida_id=d.id).delete()
        Divida.query.filter_by(cliente_id=cliente.id).delete()
        
        # Remove cliente
        db.session.delete(cliente)
        db.session.commit()
        
        return '', 200

    # ==================== CRUD - USUÁRIOS (ADMIN) ====================
    @bp.route('/admin/usuarios')
    @require_admin
    def admin_usuarios():
        """Lista todos os usuários do sistema"""
        usuarios = Usuario.query.order_by(Usuario.nome).all()
        return render_template('usuarios_list.html', usuarios=usuarios)

    @bp.route('/admin/config')
    @require_admin
    def admin_config():
        """Página de configurações administrativas"""
        clientes = Cliente.query.order_by(Cliente.nome).all()
        usuarios = Usuario.query.order_by(Usuario.nome).all()
        return render_template(
            'admin_config.html',
            clientes=clientes,
            usuarios=usuarios,
            hide_aside=True  # Oculta a sidebar de clientes nesta página
        )

    @bp.route('/admin/usuarios/novo', methods=['GET', 'POST'])
    @require_admin
    def admin_novo_usuario():
        """Cadastro de novo usuário (funcionário)"""
        if request.method == 'POST':
            nome = request.form.get('nome')
            cpf = request.form.get('cpf')
            email = request.form.get('email')
            tipo = request.form.get('tipo') or 'Caixa'
            senha = request.form.get('senha')
            
            # Valida email único
            if email and Usuario.query.filter_by(email=email).first():
                flash('Erro: Já existe um usuário cadastrado com este email.')
                return render_template('usuarios_form.html')
            
            # Valida nome único
            if Usuario.query.filter_by(nome=nome).first():
                flash('Erro: Já existe um usuário cadastrado com este nome.')
                return render_template('usuarios_form.html')
            
            # Cria e salva usuário
            usuario = Usuario(
                nome=nome,
                cpf=cpf,
                email=email,
                tipo=tipo,
                senha_hash=generate_password_hash(senha or '')
            )
            db.session.add(usuario)
            db.session.commit()
            
            flash('Usuário cadastrado com sucesso.')
            return redirect(url_for('main.admin_usuarios'))

        return render_template('usuarios_form.html')

    @bp.route('/admin/usuarios/<int:uid>/delete', methods=['POST'])
    @require_admin
    def admin_delete_usuario(uid):
        """Remove um usuário do sistema"""
        usuario = Usuario.query.get_or_404(uid)
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuário removido.')
        return redirect(url_for('main.admin_usuarios'))

    # ==================== GESTÃO FINANCEIRA ====================
    @bp.route('/dividas')
    @require_login
    def listar_dividas():
        """Lista todas as dívidas do sistema"""
        dividas = Divida.query.order_by(Divida.data_vencimento).all()
        return render_template('dividas_list.html', dividas=dividas)

    @bp.route('/dividas/novo', methods=['GET', 'POST'])
    @require_login
    def novo_divida():
        """Registra uma nova dívida (venda a prazo)"""
        clientes = Cliente.query.order_by(Cliente.nome).all()
        preselect = request.args.get('cliente_id')
        cliente_nome = None
        
        # Se vier de um cliente específico, pré-seleciona
        if preselect:
            cliente_selecionado = Cliente.query.get(int(preselect))
            if cliente_selecionado:
                cliente_nome = cliente_selecionado.nome
        
        if request.method == 'POST':
            cliente_id = int(request.form.get('cliente_id'))
            valor = float(request.form.get('valor'))
            descricao = request.form.get('descricao') or ''
            prazo = int(request.form.get('prazo') or 0)
            num_parcelas = int(request.form.get('num_parcelas') or 1)
            juros_parcelamento = float(request.form.get('juros_parcelamento') or 0.0)

            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                flash('Cliente não encontrado.')
                return redirect(url_for('main.novo_divida'))

            # COMPORTAMENTO ACUMULATIVO:
            # Atualiza prazo de todas as dívidas pendentes para o mesmo prazo da nova
            usuario_nome = session.get('user_nome', 'Sistema')
            pendentes = Divida.query.filter_by(cliente_id=cliente.id)\
                                    .filter(Divida.status != 'Paga').all()
            
            # Calcula valor total com juros (se parcelado)
            valor_total = valor
            if num_parcelas > 1 and juros_parcelamento > 0:
                valor_total = valor * (1 + juros_parcelamento / 100)
            
            # Cria nova dívida
            divida = Divida(
                cliente_id=cliente.id,
                valor_original=valor,
                saldo_devedor=valor_total,
                data_vencimento=date.today() + timedelta(days=prazo),
                descricao=descricao,
                parcelado=(num_parcelas > 1),
                num_parcelas=num_parcelas,
                juros_parcelamento=juros_parcelamento if num_parcelas > 1 else 0.0
            )
            db.session.add(divida)
            db.session.flush()  # Garante que divida.id está disponível
            
            # Se parcelado, cria as parcelas
            if num_parcelas > 1:
                from web.models import Parcela
                valor_parcela = valor_total / num_parcelas
                
                for i in range(1, num_parcelas + 1):
                    # Vencimento: mesmo dia do próximo mês (1ª parcela = +1 mês, 2ª = +2 meses, etc)
                    vencimento_parcela = date.today() + relativedelta(months=i)
                    parcela = Parcela(
                        divida_id=divida.id,
                        numero_parcela=i,
                        valor_parcela=valor_parcela,
                        data_vencimento=vencimento_parcela,
                        status='Pendente'
                    )
                    db.session.add(parcela)
                
                # Atualiza data de vencimento da dívida para a última parcela
                divida.data_vencimento = date.today() + relativedelta(months=num_parcelas)
            
            # Renegocia dívidas pendentes (após criar a nova)
            for d in pendentes:
                d.renegociar(divida.data_vencimento, 0.0, usuario_nome)
            
            db.session.commit()
            
            if num_parcelas > 1:
                flash(f'Dívida registrada com sucesso! Parcelada em {num_parcelas}x de R$ {valor_parcela:.2f}')
            else:
                flash('Dívida registrada com sucesso.')
            return redirect(url_for('main.home') + f'?cliente_id={cliente_id}')

        return render_template(
            'dividas_form.html',
            clientes=clientes,
            preselect=preselect,
            cliente_nome=cliente_nome
        )

    @bp.route('/pagamentos/novo', methods=['GET', 'POST'])
    @require_login
    def novo_pagamento():
        """Registra um novo pagamento em uma dívida"""
        cliente_id = request.args.get('cliente_id', type=int)
        
        # Filtra dívidas do cliente ou mostra todas
        if cliente_id:
            cliente = Cliente.query.get_or_404(cliente_id)
            dividas = Divida.query.filter_by(cliente_id=cliente.id)\
                                  .filter(Divida.saldo_devedor > 0).all()
        else:
            cliente = None
            dividas = Divida.query.filter(Divida.saldo_devedor > 0).all()
        
        if request.method == 'POST':
            divida_id = int(request.form.get('divida_id'))
            valor = float(request.form.get('valor'))
            meio = request.form.get('meio')
            usuario = request.form.get('usuario') or session.get('user_nome', 'Operador')
            parcela_id = request.form.get('parcela_id', type=int)

            # Registra o pagamento
            divida = Divida.query.get_or_404(divida_id)
            
            # Se for dívida parcelada, valida a parcela
            if divida.parcelado and parcela_id:
                parcela = Parcela.query.get_or_404(parcela_id)
                
                # Valida se o valor não excede o restante da parcela (com margem de 1 centavo)
                valor_restante = parcela.valor_parcela - parcela.valor_pago
                if valor > valor_restante + 0.01:
                    flash(f'Valor excede o restante da parcela (R$ {valor_restante:.2f})')
                    return redirect(url_for('main.novo_pagamento', cliente_id=cliente_id))
                
                # Atualiza a parcela
                valor_efetivo = min(valor, valor_restante)
                parcela.valor_pago += valor_efetivo
                if parcela.valor_pago >= parcela.valor_parcela - 0.01:
                    parcela.status = 'Paga'
                    parcela.valor_pago = parcela.valor_parcela
                
                db.session.add(parcela)
            
            pagamento = Pagamento(
                divida_id=divida.id,
                valor=valor,
                meio_pagamento=meio,
                usuario_responsavel=usuario
            )
            divida.registrar_pagamento(pagamento)
            db.session.commit()
            
            flash('Pagamento registrado com sucesso.')
            return redirect(url_for('main.home') + f'?cliente_id={divida.cliente_id}')

        # Preparar dados das dívidas com parcelas serializadas
        dividas_data = []
        for d in dividas:
            parcelas_list = []
            if d.parcelado:
                for p in d.parcelas:
                    parcelas_list.append({
                        'id': p.id,
                        'numero': p.numero_parcela,
                        'valor_parcela': p.valor_parcela,
                        'data_vencimento': p.data_vencimento.isoformat(),
                        'status': p.status,
                        'valor_pago': p.valor_pago
                    })
            
            dividas_data.append({
                'id': d.id,
                'descricao': d.descricao,
                'saldo_devedor': d.saldo_devedor,
                'parcelado': d.parcelado,
                'parcelas': parcelas_list
            })
        
        return render_template('pagamentos_form.html', dividas=dividas_data, cliente=cliente)

    @bp.route('/dividas/<int:divida_id>/pagar', methods=['GET', 'POST'])
    @require_login
    def pagar_divida(divida_id):
        """Formulário para pagar uma dívida específica"""
        divida = Divida.query.get_or_404(divida_id)
        
        if request.method == 'POST':
            valor = float(request.form.get('valor'))
            meio = request.form.get('meio')
            usuario = request.form.get('usuario') or session.get('user_nome', 'Operador')

            # Registra pagamento
            pagamento = Pagamento(
                divida_id=divida.id,
                valor=valor,
                meio_pagamento=meio,
                usuario_responsavel=usuario
            )
            divida.registrar_pagamento(pagamento)
            db.session.commit()
            
            flash('Pagamento registrado com sucesso.')
            return redirect(url_for('main.listar_dividas'))

        return render_template('pagar_form.html', divida=divida)

    @bp.route('/dividas/<int:divida_id>/renegociar', methods=['GET', 'POST'])
    @require_login
    def renegociar_divida(divida_id):
        """Renegocia prazo e juros de uma dívida"""
        divida = Divida.query.get_or_404(divida_id)
        
        if request.method == 'POST':
            prazo_dias = int(request.form.get('prazo_dias') or 30)
            juros = float(request.form.get('juros') or 0.0)
            usuario = session.get('user_nome', 'Operador')
            
            # Aplica renegociação
            nova_data = date.today() + timedelta(days=prazo_dias)
            divida.renegociar(nova_data, juros, usuario)
            db.session.commit()
            
            flash('Dívida renegociada com sucesso.')
            return redirect(url_for('main.home') + f'?cliente_id={divida.cliente_id}')
        
        return render_template('renegociar_form.html', divida=divida)

    @bp.route('/dividas/<int:divida_id>/apagar', methods=['POST'])
    @require_login
    def apagar_divida(divida_id):
        """
        Apaga uma dívida do sistema
        - Admin: pode apagar diretamente
        - Caixa: precisa informar credenciais de admin
        """
        divida = Divida.query.get_or_404(divida_id)
        
        # Se for caixista, valida credenciais de admin
        if session.get('user_tipo') != 'Administrador':
            data = request.get_json()
            if not data:
                return 'Credenciais de administrador necessárias', 400
            
            usuario = data.get('usuario')
            senha = data.get('senha')
            
            # Valida admin
            admin = Usuario.query.filter(
                (Usuario.nome == usuario) | (Usuario.email == usuario)
            ).first()
            
            if not admin or admin.tipo != 'Administrador' or \
               not check_password_hash(admin.senha_hash, senha):
                return 'Usuário/senha inválidos ou não é administrador', 403
        
        # Remove pagamentos e renegociações associados
        Pagamento.query.filter_by(divida_id=divida.id).delete()
        Renegociacao.query.filter_by(divida_id=divida.id).delete()
        
        # Remove a dívida
        db.session.delete(divida)
        db.session.commit()
        
        return '', 200

    # ==================== RELATÓRIOS ====================
    @bp.route('/relatorios/dashboard')
    @require_login
    def relatorio_dashboard():
        """Relatório: Dashboard consolidado (versão simplificada)"""
        dividas = Divida.query.all()
        hoje = date.today()
        
        # KPIs básicos
        total_a_receber = sum(d.saldo_devedor for d in dividas if d.status != 'Paga')
        total_vencido = sum(
            d.saldo_devedor for d in dividas
            if d.status != 'Paga' and d.data_vencimento < hoje
        )
        qtd_pagas = sum(1 for d in dividas if d.status == 'Paga')

        # Ranking de devedores
        ranking = {}
        for d in dividas:
            if d.status == 'Paga':
                continue
            nome = d.cliente.nome
            ranking[nome] = ranking.get(nome, 0) + d.saldo_devedor

        ranking_ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)

        return render_template(
            'relatorios_dashboard.html',
            total_a_receber=total_a_receber,
            total_vencido=total_vencido,
            qtd_pagas=qtd_pagas,
            ranking=ranking_ordenado[:5]
        )

    @bp.route('/relatorios/extrato', methods=['GET', 'POST'])
    @require_login
    def relatorio_extrato():
        """Relatório: Extrato de um cliente específico"""
        cliente = None
        dividas_cliente = []
        total = 0.0
        
        if request.method == 'POST':
            termo = request.form.get('termo')
            
            # Busca por ID ou nome
            if termo.isdigit():
                cliente = Cliente.query.get(int(termo))
            else:
                cliente = Cliente.query.filter(Cliente.nome.ilike(f"%{termo}%")).first()

            # Carrega dívidas do cliente
            if cliente:
                dividas_cliente = Divida.query.filter_by(cliente_id=cliente.id).all()
                total = sum(d.saldo_devedor for d in dividas_cliente)

        return render_template(
            'relatorios_extrato.html',
            cliente=cliente,
            dividas=dividas_cliente,
            total=total
        )

    # ==================== API REST (para React) ====================

    # ---------- AUTH ----------

    @bp.route('/api/auth/login', methods=['POST'])
    def api_login():
        """
        Login do usuário
        ---
        summary: Login
        tags:
          - Auth
        parameters:
          - in: body
            name: body
            schema:
              type: object
              required: [usuario, senha]
              properties:
                usuario:
                  type: string
                  example: adm
                senha:
                  type: string
                  example: adm
        responses:
          200:
            description: Login realizado com sucesso
            schema:
              type: object
              properties:
                id:
                  type: integer
                nome:
                  type: string
                tipo:
                  type: string
                  enum: [Administrador, Caixa]
          401:
            description: Credenciais inválidas
        """
        data = request.get_json() or {}
        usuario = data.get('usuario', '').strip()
        senha = data.get('senha', '')

        user = Usuario.query.filter(
            (Usuario.nome == usuario) | (Usuario.email == usuario)
        ).first()

        if not user or not check_password_hash(user.senha_hash, senha):
            return jsonify({'erro': 'Credenciais inválidas'}), 401

        session['user_id'] = user.id
        session['user_nome'] = user.nome
        session['user_tipo'] = user.tipo

        return jsonify({'id': user.id, 'nome': user.nome, 'tipo': user.tipo})

    @bp.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        """
        Logout do usuário
        ---
        summary: Logout
        tags:
          - Auth
        responses:
          200:
            description: Logout realizado
        """
        session.clear()
        return jsonify({'mensagem': 'Logout realizado'})

    @bp.route('/api/auth/me')
    def api_me():
        """
        Retorna o usuário logado
        ---
        summary: Usuário logado
        tags:
          - Auth
        responses:
          200:
            description: Dados do usuário logado
            schema:
              type: object
              properties:
                id:
                  type: integer
                nome:
                  type: string
                tipo:
                  type: string
          401:
            description: Não autenticado
        """
        if not session.get('user_id'):
            return jsonify({'erro': 'Não autenticado'}), 401
        return jsonify({
            'id': session['user_id'],
            'nome': session['user_nome'],
            'tipo': session['user_tipo']
        })

    # ---------- DASHBOARD ----------

    @bp.route('/api/dashboard')
    @require_login
    def api_dashboard():
        """
        Dados do dashboard (KPIs e gráficos)
        ---
        summary: Dashboard
        tags:
          - Dashboard
        responses:
          200:
            description: Dados consolidados do dashboard
            schema:
              type: object
              properties:
                total_a_receber:
                  type: number
                total_vencido:
                  type: number
                qtd_pagas:
                  type: integer
                qtd_vencidas:
                  type: integer
                qtd_abertas:
                  type: integer
                top_devedores:
                  type: array
                  items:
                    type: object
                    properties:
                      nome:
                        type: string
                      valor:
                        type: number
                status_counts:
                  type: object
                  properties:
                    pagas:
                      type: integer
                    em_dia:
                      type: integer
                    renegociadas:
                      type: integer
                    vencidas:
                      type: integer
                dividas_vencidas:
                  type: array
                  items:
                    type: object
                month_labels:
                  type: array
                  items:
                    type: string
                month_values:
                  type: array
                  items:
                    type: number
        """
        import calendar as cal
        dividas = Divida.query.all()
        pagamentos = Pagamento.query.all()
        hoje = date.today()

        total_a_receber = sum(d.saldo_devedor for d in dividas if d.status != 'Paga')
        total_vencido = sum(
            d.saldo_devedor for d in dividas
            if d.status != 'Paga' and d.data_vencimento <= hoje
        )
        qtd_pagas = sum(1 for d in dividas if d.status == 'Paga')
        qtd_vencidas = sum(1 for d in dividas if d.status != 'Paga' and d.data_vencimento < hoje)
        qtd_abertas = sum(1 for d in dividas if d.status != 'Paga' and d.data_vencimento >= hoje)

        ranking = {}
        for d in dividas:
            if d.status == 'Paga':
                continue
            ranking[d.cliente.nome] = ranking.get(d.cliente.nome, 0) + d.saldo_devedor
        top_devedores = [
            {'nome': n, 'valor': round(v, 2)}
            for n, v in sorted(ranking.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        pagas_ct = em_dia_ct = renegociadas_ct = vencidas_ct = 0
        for d in dividas:
            if d.status == 'Paga' or d.saldo_devedor <= 0:
                pagas_ct += 1
            elif d.data_vencimento <= hoje and d.saldo_devedor > 0:
                vencidas_ct += 1
            elif d.status == 'Renegociada' and d.saldo_devedor > 0:
                renegociadas_ct += 1
            elif d.saldo_devedor > 0:
                em_dia_ct += 1

        meio_map = {}
        for p in pagamentos:
            meio = p.meio_pagamento or 'Outro'
            meio_map[meio] = meio_map.get(meio, 0) + 1

        by_month = defaultdict(float)
        for d in dividas:
            if d.data_venda:
                by_month[(d.data_venda.year, d.data_venda.month)] += float(d.valor_original or 0)

        month_labels, month_values = [], []
        ref = date(hoje.year, hoje.month, 1)
        for i in range(5, -1, -1):
            ano, mes = ref.year, ref.month - i
            while mes <= 0:
                ano -= 1
                mes += 12
            month_labels.append(f"{cal.month_abbr[mes]}/{str(ano)[-2:]}")
            month_values.append(round(by_month.get((ano, mes), 0.0), 2))

        dividas_vencidas = [
            {
                'id': d.id,
                'cliente_nome': d.cliente.nome,
                'descricao': d.descricao or '',
                'saldo': d.saldo_devedor,
                'vencimento': d.data_vencimento.isoformat()
            }
            for d in sorted(
                [d for d in dividas if d.status != 'Paga' and d.saldo_devedor > 0 and d.data_vencimento <= hoje],
                key=lambda x: x.data_vencimento
            )
        ]

        return jsonify({
            'total_a_receber': round(total_a_receber, 2),
            'total_vencido': round(total_vencido, 2),
            'qtd_pagas': qtd_pagas,
            'qtd_vencidas': qtd_vencidas,
            'qtd_abertas': qtd_abertas,
            'top_devedores': top_devedores,
            'status_counts': {
                'pagas': pagas_ct,
                'em_dia': em_dia_ct,
                'renegociadas': renegociadas_ct,
                'vencidas': vencidas_ct
            },
            'meios_pagamento': meio_map,
            'month_labels': month_labels,
            'month_values': month_values,
            'dividas_vencidas': dividas_vencidas
        })

    # ---------- CLIENTES ----------

    @bp.route('/api/clientes', methods=['POST'])
    @require_login
    def api_criar_cliente():
        """
        Cria um novo cliente
        ---
        summary: Criar cliente
        tags:
          - Clientes
        parameters:
          - in: body
            name: body
            schema:
              type: object
              required: [nome]
              properties:
                nome:
                  type: string
                cpf:
                  type: string
                celular:
                  type: string
                endereco:
                  type: string
                nivel:
                  type: string
                  enum: [Novo, Bronze, Prata, Ouro]
                limite:
                  type: number
        responses:
          201:
            description: Cliente criado
          409:
            description: Cliente já existe
        """
        data = request.get_json() or {}
        nome = data.get('nome', '').strip()

        if not nome:
            return jsonify({'erro': 'Nome é obrigatório'}), 400
        
        cpf = data.get('cpf')
        if cpf and len(''.join(filter(str.isdigit, cpf))) != 11:
            return jsonify({'erro': 'CPF deve conter 11 números'}), 400
        
        if Cliente.query.filter_by(nome=nome).first():
            return jsonify({'erro': 'Já existe um cliente com este nome'}), 409

        cliente = Cliente(
            nome=nome,
            cpf=data.get('cpf'),
            celular=data.get('celular'),
            endereco=data.get('endereco'),
            nivel_confianca=data.get('nivel', 'Novo'),
            limite_credito=float(data.get('limite', 200.0))
        )
        db.session.add(cliente)
        db.session.commit()

        return jsonify({'id': cliente.id, 'nome': cliente.nome}), 201

    @bp.route('/api/clientes/<int:cliente_id>', methods=['DELETE'])
    @require_admin
    def api_apagar_cliente(cliente_id):
        """
        Remove um cliente e todos os dados associados
        ---
        summary: Remover cliente
        tags:
          - Clientes
        parameters:
          - name: cliente_id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Cliente removido
          404:
            description: Cliente não encontrado
        """
        cliente = Cliente.query.get_or_404(cliente_id)
        dividas = Divida.query.filter_by(cliente_id=cliente.id).all()
        for d in dividas:
            Pagamento.query.filter_by(divida_id=d.id).delete()
            Renegociacao.query.filter_by(divida_id=d.id).delete()
        Divida.query.filter_by(cliente_id=cliente.id).delete()
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({'mensagem': 'Cliente removido'})

    # ---------- USUÁRIOS ----------

    @bp.route('/api/usuarios')
    @require_admin
    def api_listar_usuarios():
        """
        Lista todos os usuários do sistema
        ---
        summary: Lista usuários
        tags:
          - Usuários
        responses:
          200:
            description: Lista de usuários
            schema:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  nome:
                    type: string
                  email:
                    type: string
                  tipo:
                    type: string
                    enum: [Administrador, Caixa]
                  ativo:
                    type: boolean
        """
        usuarios = Usuario.query.order_by(Usuario.nome).all()
        return jsonify([
            {'id': u.id, 'nome': u.nome, 'email': u.email, 'tipo': u.tipo, 'ativo': u.ativo}
            for u in usuarios
        ])

    @bp.route('/api/usuarios', methods=['POST'])
    @require_admin
    def api_criar_usuario():
        """
        Cria um novo usuário
        ---
        summary: Criar usuário
        tags:
          - Usuários
        parameters:
          - in: body
            name: body
            schema:
              type: object
              required: [nome, senha]
              properties:
                nome:
                  type: string
                cpf:
                  type: string
                email:
                  type: string
                tipo:
                  type: string
                  enum: [Administrador, Caixa]
                senha:
                  type: string
        responses:
          201:
            description: Usuário criado
          409:
            description: Usuário já existe
        """
        data = request.get_json() or {}
        nome = data.get('nome', '').strip()
        email = data.get('email', '').strip() or None
        senha = data.get('senha', '')

        if not nome or not senha:
            return jsonify({'erro': 'Nome e senha são obrigatórios'}), 400

        if email and Usuario.query.filter_by(email=email).first():
            return jsonify({'erro': 'Email já cadastrado'}), 409

        if Usuario.query.filter_by(nome=nome).first():
            return jsonify({'erro': 'Nome já cadastrado'}), 409

        usuario = Usuario(
            nome=nome,
            cpf=data.get('cpf'),
            email=email,
            tipo=data.get('tipo', 'Caixa'),
            senha_hash=generate_password_hash(senha, method='pbkdf2:sha256')
        )
        db.session.add(usuario)
        db.session.commit()

        return jsonify({'id': usuario.id, 'nome': usuario.nome}), 201

    @bp.route('/api/usuarios/<int:uid>', methods=['DELETE'])
    @require_admin
    def api_deletar_usuario(uid):
        """
        Remove um usuário
        ---
        summary: Remover usuário
        tags:
          - Usuários
        parameters:
          - name: uid
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Usuário removido
          404:
            description: Usuário não encontrado
        """
        usuario = Usuario.query.get_or_404(uid)
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({'mensagem': 'Usuário removido'})

    # ---------- DÍVIDAS ----------

    @bp.route('/api/dividas')
    @require_login
    def api_listar_dividas():
        """
        Lista todas as dívidas
        ---
        summary: Lista dívidas
        tags:
          - Dívidas
        parameters:
          - name: cliente_id
            in: query
            type: integer
            required: false
            description: Filtrar por cliente
          - name: status
            in: query
            type: string
            required: false
            description: Filtrar por status (Pendente, Paga, Renegociada)
        responses:
          200:
            description: Lista de dívidas
        """
        cliente_id = request.args.get('cliente_id', type=int)
        status = request.args.get('status')

        query = Divida.query
        if cliente_id:
            query = query.filter_by(cliente_id=cliente_id)
        if status:
            query = query.filter_by(status=status)

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        dividas = query.order_by(Divida.data_vencimento).paginate(page=page, per_page=per_page, error_out=False).items
        return jsonify([
            {
                'id': d.id,
                'cliente_id': d.cliente_id,
                'cliente_nome': d.cliente.nome,
                'valor_original': d.valor_original,
                'saldo_devedor': d.saldo_devedor,
                'data_venda': d.data_venda.isoformat() if d.data_venda else None,
                'data_vencimento': d.data_vencimento.isoformat(),
                'status': d.status,
                'descricao': d.descricao,
                'parcelado': d.parcelado,
                'num_parcelas': d.num_parcelas,
                'juros_parcelamento': d.juros_parcelamento
            }
            for d in dividas
        ])

    @bp.route('/api/dividas', methods=['POST'])
    @require_login
    def api_criar_divida():
        """
        Registra uma nova dívida
        ---
        summary: Criar dívida
        tags:
          - Dívidas
        parameters:
          - in: body
            name: body
            schema:
              type: object
              required: [cliente_id, valor]
              properties:
                cliente_id:
                  type: integer
                valor:
                  type: number
                descricao:
                  type: string
                prazo:
                  type: integer
                  description: Prazo em dias
                num_parcelas:
                  type: integer
                  default: 1
                juros_parcelamento:
                  type: number
                  default: 0
        responses:
          201:
            description: Dívida criada
          404:
            description: Cliente não encontrado
        """
        data = request.get_json() or {}
        cliente_id = data.get('cliente_id')
        valor = float(data.get('valor', 0))
        prazo = int(data.get('prazo', 0))
        num_parcelas = int(data.get('num_parcelas', 1))
        juros_parcelamento = float(data.get('juros_parcelamento', 0.0))

        cliente = Cliente.query.get(cliente_id)
        if not cliente:
            return jsonify({'erro': 'Cliente não encontrado'}), 404

        valor_total = valor
        if num_parcelas > 1 and juros_parcelamento > 0:
            valor_total = valor * (1 + juros_parcelamento / 100)

        divida = Divida(
            cliente_id=cliente.id,
            valor_original=valor,
            saldo_devedor=valor_total,
            data_vencimento=date.today() + timedelta(days=prazo),
            descricao=data.get('descricao', ''),
            parcelado=(num_parcelas > 1),
            num_parcelas=num_parcelas,
            juros_parcelamento=juros_parcelamento if num_parcelas > 1 else 0.0
        )
        db.session.add(divida)
        db.session.flush()

        if num_parcelas > 1:
            from web.models import Parcela
            valor_parcela = valor_total / num_parcelas
            for i in range(1, num_parcelas + 1):
                parcela = Parcela(
                    divida_id=divida.id,
                    numero_parcela=i,
                    valor_parcela=valor_parcela,
                    data_vencimento=date.today() + relativedelta(months=i),
                    status='Pendente'
                )
                db.session.add(parcela)
            divida.data_vencimento = date.today() + relativedelta(months=num_parcelas)

        usuario_nome = session.get('user_nome', 'Sistema')
        pendentes = Divida.query.filter_by(cliente_id=cliente.id)\
                                .filter(Divida.status != 'Paga').all()
        for d in pendentes:
            if d.id != divida.id:
                d.renegociar(divida.data_vencimento, 0.0, usuario_nome)

        db.session.commit()

        return jsonify({'id': divida.id, 'saldo_devedor': divida.saldo_devedor}), 201

    @bp.route('/api/dividas/<int:divida_id>', methods=['DELETE'])
    @require_login
    def api_apagar_divida(divida_id):
        """
        Remove uma dívida (caixa requer credenciais de admin)
        ---
        summary: Remover dívida
        tags:
          - Dívidas
        parameters:
          - name: divida_id
            in: path
            type: integer
            required: true
          - in: body
            name: body
            schema:
              type: object
              description: Necessário apenas para usuário Caixa
              properties:
                usuario:
                  type: string
                senha:
                  type: string
        responses:
          200:
            description: Dívida removida
          403:
            description: Acesso negado
        """
        divida = Divida.query.get_or_404(divida_id)

        if session.get('user_tipo') != 'Administrador':
            data = request.get_json() or {}
            admin = Usuario.query.filter(
                (Usuario.nome == data.get('usuario')) | (Usuario.email == data.get('usuario'))
            ).first()
            if not admin or admin.tipo != 'Administrador' or \
               not check_password_hash(admin.senha_hash, data.get('senha', '')):
                return jsonify({'erro': 'Credenciais de administrador inválidas'}), 403

        Pagamento.query.filter_by(divida_id=divida.id).delete()
        Renegociacao.query.filter_by(divida_id=divida.id).delete()
        db.session.delete(divida)
        db.session.commit()

        return jsonify({'mensagem': 'Dívida removida'})

    @bp.route('/api/dividas/<int:divida_id>/renegociar', methods=['POST'])
    @require_login
    def api_renegociar_divida(divida_id):
        """
        Renegocia prazo e juros de uma dívida
        ---
        summary: Renegociar dívida
        tags:
          - Dívidas
        parameters:
          - name: divida_id
            in: path
            type: integer
            required: true
          - in: body
            name: body
            schema:
              type: object
              properties:
                prazo_dias:
                  type: integer
                  default: 30
                juros:
                  type: number
                  default: 0
        responses:
          200:
            description: Dívida renegociada
        """
        divida = Divida.query.get_or_404(divida_id)
        data = request.get_json() or {}
        prazo_dias = int(data.get('prazo_dias', 30))
        juros = float(data.get('juros', 0.0))

        nova_data = date.today() + timedelta(days=prazo_dias)
        divida.renegociar(nova_data, juros, session.get('user_nome', 'Operador'))
        db.session.commit()

        return jsonify({
            'mensagem': 'Dívida renegociada',
            'novo_vencimento': nova_data.isoformat(),
            'novo_saldo': divida.saldo_devedor
        })

    # ---------- PAGAMENTOS ----------

    @bp.route('/api/pagamentos', methods=['POST'])
    @require_login
    def api_registrar_pagamento():
        """
        Registra um pagamento em uma dívida
        ---
        summary: Registrar pagamento
        tags:
          - Pagamentos
        parameters:
          - in: body
            name: body
            schema:
              type: object
              required: [divida_id, valor, meio]
              properties:
                divida_id:
                  type: integer
                valor:
                  type: number
                meio:
                  type: string
                  enum: [Dinheiro, Pix, Cartão, Cheque]
                parcela_id:
                  type: integer
                  description: Obrigatório se a dívida for parcelada
        responses:
          200:
            description: Pagamento registrado
          400:
            description: Valor excede o restante da parcela
        """
        data = request.get_json() or {}
        divida_id = data.get('divida_id')
        valor = float(data.get('valor', 0))
        meio = data.get('meio')
        parcela_id = data.get('parcela_id')

        divida = Divida.query.get_or_404(divida_id)

        if divida.parcelado and parcela_id:
            from web.models import Parcela
            parcela = Parcela.query.get_or_404(parcela_id)
            valor_restante = parcela.valor_parcela - parcela.valor_pago
            if valor > valor_restante + 0.01:
                return jsonify({'erro': f'Valor excede o restante da parcela (R$ {valor_restante:.2f})'}), 400

            valor_efetivo = min(valor, valor_restante)
            parcela.valor_pago += valor_efetivo
            if parcela.valor_pago >= parcela.valor_parcela - 0.01:
                parcela.status = 'Paga'
                parcela.valor_pago = parcela.valor_parcela
            db.session.add(parcela)

        pagamento = Pagamento(
            divida_id=divida.id,
            valor=valor,
            meio_pagamento=meio,
            usuario_responsavel=session.get('user_nome', 'Operador')
        )
        divida.registrar_pagamento(pagamento)
        db.session.commit()

        return jsonify({
            'mensagem': 'Pagamento registrado',
            'saldo_devedor': divida.saldo_devedor,
            'status': divida.status
        })

    # ---------- RELATÓRIOS ----------

    @bp.route('/api/relatorios/extrato')
    @require_login
    def api_extrato():
        """
        Extrato de um cliente
        ---
        summary: Extrato do cliente
        tags:
          - Relatórios
        parameters:
          - name: cliente_id
            in: query
            type: integer
            required: true
        responses:
          200:
            description: Extrato do cliente
          404:
            description: Cliente não encontrado
        """
        cliente_id = request.args.get('cliente_id', type=int)
        if not cliente_id:
            return jsonify({'erro': 'cliente_id é obrigatório'}), 400

        cliente = Cliente.query.get_or_404(cliente_id)
        dividas = Divida.query.filter_by(cliente_id=cliente.id).all()
        total = sum(d.saldo_devedor for d in dividas)

        return jsonify({
            'cliente': {'id': cliente.id, 'nome': cliente.nome, 'celular': cliente.celular},
            'total_devedor': round(total, 2),
            'dividas': [
                {
                    'id': d.id,
                    'valor_original': d.valor_original,
                    'saldo_devedor': d.saldo_devedor,
                    'data_vencimento': d.data_vencimento.isoformat(),
                    'status': d.status,
                    'descricao': d.descricao
                }
                for d in dividas
            ]
        })

    # Registra todas as rotas no Flask
    @bp.route('/api/health')
    def api_health():
      """Verifica se a API está no ar"""
      return jsonify({'status': 'ok'})
    app.register_blueprint(bp)
