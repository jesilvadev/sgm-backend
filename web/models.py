"""
Modelos de Dados do SGM - Sistema de Gerenciamento de Mercearia

Define as tabelas do banco de dados e suas relações:
- Usuario: funcionários do sistema (Admin ou Caixa)
- Cliente: clientes que fazem compras fiado
- Divida: registro de compras a prazo
- Pagamento: pagamentos realizados nas dívidas
- Renegociacao: histórico de renegociações de prazo/juros
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import date

# Inicializa o SQLAlchemy para gerenciar o banco de dados
db = SQLAlchemy()


class Usuario(db.Model):
    """Modelo de Usuário do sistema (Administrador ou Caixa)"""
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False, unique=True)
    cpf = db.Column(db.String(20), unique=True, nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False, default='Caixa')  # 'Administrador' ou 'Caixa'
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Usuario {self.nome} ({self.tipo})>"

class Cliente(db.Model):
    """Modelo de Cliente - pessoas que compram fiado na mercearia"""
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False, unique=True)
    cpf = db.Column(db.String(20), nullable=True)
    celular = db.Column(db.String(50), nullable=True)
    endereco = db.Column(db.String(255), nullable=True)
    nivel_confianca = db.Column(db.String(50), default='Novo')  # Novo, Bronze, Prata, Ouro
    limite_credito = db.Column(db.Float, default=200.0)  # Limite de crédito em R$
    notificacoes_ativas = db.Column(db.Boolean, default=True)

    # Relacionamento: um cliente pode ter várias dívidas
    dividas = db.relationship('Divida', backref='cliente', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Cliente {self.nome}>"

class Divida(db.Model):
    """Modelo de Dívida - registro de compra a prazo (fiado)"""
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    valor_original = db.Column(db.Float, nullable=False)  # Valor total da compra
    data_venda = db.Column(db.Date, default=date.today)  # Data da compra
    data_vencimento = db.Column(db.Date, nullable=False)  # Prazo para pagamento
    descricao = db.Column(db.String(255), default='')  # Descrição dos itens
    status = db.Column(db.String(50), default='Pendente')  # Pendente, Paga, Renegociada
    saldo_devedor = db.Column(db.Float, nullable=False)  # Quanto ainda falta pagar
    
    # Campos de parcelamento
    parcelado = db.Column(db.Boolean, default=False)  # Se foi parcelado
    num_parcelas = db.Column(db.Integer, default=1)  # Quantidade de parcelas
    juros_parcelamento = db.Column(db.Float, default=0.0)  # Juros aplicados no parcelamento

    # Relacionamentos: uma dívida pode ter vários pagamentos, renegociações e parcelas
    pagamentos = db.relationship('Pagamento', backref='divida', lazy=True, cascade='all, delete-orphan')
    renegociacoes = db.relationship('Renegociacao', backref='divida', lazy=True, cascade='all, delete-orphan')
    parcelas = db.relationship('Parcela', backref='divida', lazy=True, cascade='all, delete-orphan')

    def aplicar_pagamento(self, pagamento):
        """Aplica um pagamento na dívida, reduzindo o saldo devedor"""
        self.saldo_devedor -= pagamento.valor
        
        # Se pagou tudo (ou mais), marca como paga
        if self.saldo_devedor <= 0:
            self.saldo_devedor = 0.0
            self.status = 'Paga'

    def registrar_pagamento(self, pagamento):
        """Registra um pagamento no banco e atualiza o saldo"""
        db.session.add(pagamento)
        self.aplicar_pagamento(pagamento)

    def renegociar(self, nova_data, juros_percent, usuario_responsavel):
        """Renegocia a dívida: aplica juros e prorroga o prazo"""
        # Calcula e aplica juros
        acrescimo = self.saldo_devedor * (juros_percent / 100)
        self.saldo_devedor += acrescimo
        
        # Atualiza prazo e status
        self.data_vencimento = nova_data
        self.status = 'Renegociada'
        
        # Registra no histórico de renegociações
        reneg = Renegociacao(
            divida_id=self.id,
            nova_data_venc=nova_data,
            juros_percent=juros_percent,
            usuario_responsavel=usuario_responsavel
        )
        db.session.add(reneg)

    def __repr__(self):
        return f"<Divida #{self.id} - Cliente: {self.cliente.nome} - Saldo: R${self.saldo_devedor:.2f}>"

class Pagamento(db.Model):
    """Modelo de Pagamento - registro de pagamento parcial ou total de uma dívida"""
    
    id = db.Column(db.Integer, primary_key=True)
    divida_id = db.Column(db.Integer, db.ForeignKey('divida.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)  # Valor pago
    data_pagamento = db.Column(db.Date, default=date.today)
    meio_pagamento = db.Column(db.String(50), nullable=True)  # Dinheiro, Pix, Cartão, etc.
    usuario_responsavel = db.Column(db.String(150), nullable=True)  # Quem registrou o pagamento

    def __repr__(self):
        return f"<Pagamento R${self.valor:.2f} - {self.data_pagamento}>"


class Renegociacao(db.Model):
    """Modelo de Renegociação - histórico de alterações de prazo e juros"""
    
    id = db.Column(db.Integer, primary_key=True)
    divida_id = db.Column(db.Integer, db.ForeignKey('divida.id'), nullable=False)
    nova_data_venc = db.Column(db.Date, nullable=False)  # Novo prazo acordado
    juros_percent = db.Column(db.Float, nullable=False)  # Percentual de juros aplicado
    data_reneg = db.Column(db.Date, default=date.today)  # Data da renegociação
    usuario_responsavel = db.Column(db.String(150), nullable=True)  # Quem fez a renegociação

    def __repr__(self):
        return f"<Renegociacao - Novo vencimento: {self.nova_data_venc} - Juros: {self.juros_percent}%>"


class Parcela(db.Model):
    """Modelo de Parcela - representa uma parcela de uma dívida parcelada"""
    
    id = db.Column(db.Integer, primary_key=True)
    divida_id = db.Column(db.Integer, db.ForeignKey('divida.id'), nullable=False)
    numero_parcela = db.Column(db.Integer, nullable=False)  # 1, 2, 3...
    valor_parcela = db.Column(db.Float, nullable=False)  # Valor da parcela
    data_vencimento = db.Column(db.Date, nullable=False)  # Vencimento desta parcela
    status = db.Column(db.String(50), default='Pendente')  # Pendente, Paga, Vencida
    valor_pago = db.Column(db.Float, default=0.0)  # Quanto já foi pago desta parcela
    
    def __repr__(self):
        return f"<Parcela {self.numero_parcela} - R${self.valor_parcela:.2f} - {self.status}>"
