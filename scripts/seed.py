from app import create_app
from web.models import db, Usuario, Cliente, Divida, Pagamento, Renegociacao, Parcela
from werkzeug.security import generate_password_hash
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import random

app = create_app()

with app.app_context():
    # Limpar dados existentes
    print('🗑️ Limpando banco de dados...')
    db.drop_all()
    db.create_all()
    
    # Usuários
    print('👥 Criando usuários...')
    admin = Usuario(nome='adm', senha_hash=generate_password_hash('adm'), tipo='Administrador')
    caixa = Usuario(nome='caixa', senha_hash=generate_password_hash('caixa'), tipo='Caixa')
    gerente = Usuario(nome='gerente', senha_hash=generate_password_hash('gerente'), tipo='Administrador')
    db.session.add_all([admin, caixa, gerente])
    db.session.commit()

    # Clientes - Expandido para 20 clientes
    print('🧑 Criando clientes...')
    clientes_data = [
        {'nome': 'Aline Souza', 'cpf': '11111111111', 'celular': '11999990001', 'endereco': 'Rua das Flores, 123'},
        {'nome': 'Bruno Lima', 'cpf': '22222222222', 'celular': '11999990002', 'endereco': 'Av. Central, 456'},
        {'nome': 'Carla Dias', 'cpf': '33333333333', 'celular': '11999990003', 'endereco': 'Rua do Comércio, 789'},
        {'nome': 'Daniela Alves', 'cpf': '44444444444', 'celular': '11999990004', 'endereco': 'Travessa São João, 101'},
        {'nome': 'Eduardo Silva', 'cpf': '55555555555', 'celular': '11999990005', 'endereco': 'Rua Verde, 202'},
        {'nome': 'Fernanda Costa', 'cpf': '66666666666', 'celular': '11999990006', 'endereco': 'Av. Paulista, 303'},
        {'nome': 'Gustavo Rocha', 'cpf': '77777777777', 'celular': '11999990007', 'endereco': 'Rua Azul, 404'},
        {'nome': 'Helena Martins', 'cpf': '88888888888', 'celular': '11999990008', 'endereco': 'Rua Amarela, 505'},
        {'nome': 'Igor Mendes', 'cpf': '99999999999', 'celular': '11999990009', 'endereco': 'Rua Vermelha, 606'},
        {'nome': 'Juliana Prado', 'cpf': '10101010101', 'celular': '11999990010', 'endereco': 'Av. Brasil, 707'},
        {'nome': 'Lucas Oliveira', 'cpf': '12121212121', 'celular': '11999990011', 'endereco': 'Rua da Paz, 808'},
        {'nome': 'Marina Santos', 'cpf': '13131313131', 'celular': '11999990012', 'endereco': 'Rua Esperança, 909'},
        {'nome': 'Nicolas Ferreira', 'cpf': '14141414141', 'celular': '11999990013', 'endereco': 'Av. Liberdade, 1010'},
        {'nome': 'Olivia Rodrigues', 'cpf': '15151515151', 'celular': '11999990014', 'endereco': 'Rua Alegria, 1111'},
        {'nome': 'Paulo Gonçalves', 'cpf': '16161616161', 'celular': '11999990015', 'endereco': 'Rua Nova, 1212'},
        {'nome': 'Quitéria Barbosa', 'cpf': '17171717171', 'celular': '11999990016', 'endereco': 'Travessa Antiga, 1313'},
        {'nome': 'Rafael Cardoso', 'cpf': '18181818181', 'celular': '11999990017', 'endereco': 'Rua do Sol, 1414'},
        {'nome': 'Sabrina Mendes', 'cpf': '19191919191', 'celular': '11999990018', 'endereco': 'Av. da Lua, 1515'},
        {'nome': 'Thiago Araújo', 'cpf': '20202020202', 'celular': '11999990019', 'endereco': 'Rua das Estrelas, 1616'},
        {'nome': 'Vanessa Lima', 'cpf': '21212121212', 'celular': '11999990020', 'endereco': 'Rua do Horizonte, 1717'},
    ]
    clientes = []
    for cdata in clientes_data:
        c = Cliente(**cdata)
        db.session.add(c)
        clientes.append(c)
    db.session.commit()

    # Dívidas variadas: vencidas, em dia, pagas, renegociadas, parceladas
    print('💰 Criando dívidas diversas...')
    hoje = date.today()
    descricoes = ['Compras do mês', 'Produtos alimentícios', 'Bebidas', 'Limpeza', 'Higiene pessoal', 
                  'Hortifruti', 'Congelados', 'Padaria', 'Açougue', 'Diversos']
    meios_pagamento = ['Dinheiro', 'Pix', 'Cartão Débito', 'Cartão Crédito']
    
    dividas_criadas = []
    
    for cliente in clientes:
        # Cada cliente tem entre 3 e 6 dívidas
        num_dividas = random.randint(3, 6)
        
        for i in range(num_dividas):
            tipo = random.choice(['vencida', 'em_dia', 'paga', 'renegociada', 'parcelada'])
            valor = random.randint(50, 500)
            descricao = random.choice(descricoes)
            
            if tipo == 'vencida':
                # Dívida vencida sem pagamentos
                divida = Divida(
                    cliente_id=cliente.id,
                    valor_original=valor,
                    saldo_devedor=valor,
                    data_venda=hoje - timedelta(days=random.randint(40, 90)),
                    data_vencimento=hoje - timedelta(days=random.randint(5, 30)),
                    descricao=f'{descricao} (vencida)',
                    status='Pendente',
                    parcelado=False,
                    num_parcelas=1,
                    juros_parcelamento=0.0
                )
                db.session.add(divida)
                
            elif tipo == 'em_dia':
                # Dívida em dia, com ou sem pagamentos parciais
                divida = Divida(
                    cliente_id=cliente.id,
                    valor_original=valor,
                    saldo_devedor=valor,
                    data_venda=hoje - timedelta(days=random.randint(1, 15)),
                    data_vencimento=hoje + timedelta(days=random.randint(10, 40)),
                    descricao=f'{descricao} (em dia)',
                    status='Pendente',
                    parcelado=False,
                    num_parcelas=1,
                    juros_parcelamento=0.0
                )
                db.session.add(divida)
                db.session.flush()
                
                # 50% de chance de ter pagamento parcial
                if random.choice([True, False]):
                    valor_pago = random.randint(20, valor // 2)
                    pagamento = Pagamento(
                        divida_id=divida.id,
                        valor=valor_pago,
                        meio_pagamento=random.choice(meios_pagamento),
                        usuario_responsavel='caixa'
                    )
                    divida.registrar_pagamento(pagamento)
                    
            elif tipo == 'paga':
                # Dívida totalmente paga
                divida = Divida(
                    cliente_id=cliente.id,
                    valor_original=valor,
                    saldo_devedor=0,
                    data_venda=hoje - timedelta(days=random.randint(20, 60)),
                    data_vencimento=hoje - timedelta(days=random.randint(1, 20)),
                    descricao=f'{descricao} (paga)',
                    status='Paga',
                    parcelado=False,
                    num_parcelas=1,
                    juros_parcelamento=0.0
                )
                db.session.add(divida)
                db.session.flush()
                
                # Criar 1 a 3 pagamentos que somam o valor total
                num_pagamentos = random.randint(1, 3)
                valores_pagos = []
                resto = valor
                for j in range(num_pagamentos - 1):
                    v = random.randint(10, resto // 2)
                    valores_pagos.append(v)
                    resto -= v
                valores_pagos.append(resto)
                
                for v_pago in valores_pagos:
                    pagamento = Pagamento(
                        divida_id=divida.id,
                        valor=v_pago,
                        meio_pagamento=random.choice(meios_pagamento),
                        usuario_responsavel=random.choice(['adm', 'caixa'])
                    )
                    divida.registrar_pagamento(pagamento)
                    
            elif tipo == 'renegociada':
                # Dívida que foi vencida e renegociada
                divida = Divida(
                    cliente_id=cliente.id,
                    valor_original=valor,
                    saldo_devedor=valor * 1.10,  # 10% de juros na renegociação
                    data_venda=hoje - timedelta(days=random.randint(50, 100)),
                    data_vencimento=hoje + timedelta(days=random.randint(20, 50)),
                    descricao=f'{descricao} (renegociada)',
                    status='Renegociada',
                    parcelado=False,
                    num_parcelas=1,
                    juros_parcelamento=0.0
                )
                db.session.add(divida)
                db.session.flush()
                
                # Criar renegociação
                renegociacao = Renegociacao(
                    divida_id=divida.id,
                    nova_data_venc=divida.data_vencimento,
                    juros_percent=10.0,
                    usuario_responsavel='gerente'
                )
                db.session.add(renegociacao)
                
                # 70% de chance de ter pagamento parcial
                if random.random() < 0.7:
                    valor_max = max(30, int(divida.saldo_devedor // 2))
                    valor_pago = random.randint(30, valor_max)
                    pagamento = Pagamento(
                        divida_id=divida.id,
                        valor=valor_pago,
                        meio_pagamento=random.choice(meios_pagamento),
                        usuario_responsavel='caixa'
                    )
                    divida.registrar_pagamento(pagamento)
                    
            elif tipo == 'parcelada':
                # Dívida parcelada com ou sem juros
                num_parcelas = random.choice([2, 3, 4, 6, 10, 12])
                tem_juros = random.choice([True, False])
                juros = random.choice([0.0, 2.0, 3.5, 5.0, 8.0, 10.0]) if tem_juros else 0.0
                
                valor_total = valor * (1 + juros / 100) if tem_juros else valor
                valor_parcela = valor_total / num_parcelas
                
                data_venda = hoje - timedelta(days=random.randint(1, 30))
                
                divida = Divida(
                    cliente_id=cliente.id,
                    valor_original=valor,
                    saldo_devedor=valor_total,
                    data_venda=data_venda,
                    data_vencimento=data_venda + relativedelta(months=num_parcelas),
                    descricao=f'{descricao} ({num_parcelas}x)',
                    status='Pendente',
                    parcelado=True,
                    num_parcelas=num_parcelas,
                    juros_parcelamento=juros
                )
                db.session.add(divida)
                db.session.flush()
                
                # Criar parcelas (mesma data do mês seguinte)
                for parcela_num in range(1, num_parcelas + 1):
                    vencimento_parcela = data_venda + relativedelta(months=parcela_num)
                    
                    # Define status da parcela baseado no vencimento e se foi paga
                    if vencimento_parcela < hoje:
                        status_parcela = 'Vencida'
                    else:
                        status_parcela = 'Pendente'
                    
                    # 30% de chance de parcelas já vencidas terem sido pagas
                    valor_pago_parcela = 0
                    if status_parcela == 'Vencida' and random.random() < 0.3:
                        status_parcela = 'Paga'
                        valor_pago_parcela = valor_parcela
                        
                        # Registrar pagamento da parcela
                        pagamento = Pagamento(
                            divida_id=divida.id,
                            valor=valor_parcela,
                            meio_pagamento=random.choice(meios_pagamento),
                            usuario_responsavel=random.choice(['adm', 'caixa'])
                        )
                        divida.registrar_pagamento(pagamento)
                    
                    parcela = Parcela(
                        divida_id=divida.id,
                        numero_parcela=parcela_num,
                        valor_parcela=valor_parcela,
                        data_vencimento=vencimento_parcela,
                        status=status_parcela,
                        valor_pago=valor_pago_parcela
                    )
                    db.session.add(parcela)
            
            dividas_criadas.append(divida)
    
    db.session.commit()
    
    # Estatísticas
    total_clientes = len(clientes)
    total_dividas = len(dividas_criadas)
    total_vencidas = sum(1 for d in dividas_criadas if d.status == 'Pendente' and d.data_vencimento < hoje)
    total_em_dia = sum(1 for d in dividas_criadas if d.status == 'Pendente' and d.data_vencimento >= hoje)
    total_pagas = sum(1 for d in dividas_criadas if d.status == 'Paga')
    total_renegociadas = sum(1 for d in dividas_criadas if d.status == 'Renegociada')
    total_parceladas = sum(1 for d in dividas_criadas if d.parcelado)
    total_pagamentos = Pagamento.query.count()
    total_renegociacoes = Renegociacao.query.count()
    total_parcelas = Parcela.query.count()
    
    print('\n✅ Seed concluído com sucesso!')
    print('=' * 50)
    print(f'👥 Usuários criados: 3')
    print(f'🧑 Clientes criados: {total_clientes}')
    print(f'💰 Dívidas criadas: {total_dividas}')
    print(f'  ├─ ⏰ Vencidas: {total_vencidas}')
    print(f'  ├─ ✅ Em dia: {total_em_dia}')
    print(f'  ├─ 💚 Pagas: {total_pagas}')
    print(f'  ├─ 🔄 Renegociadas: {total_renegociadas}')
    print(f'  └─ 📊 Parceladas: {total_parceladas}')
    print(f'💵 Pagamentos registrados: {total_pagamentos}')
    print(f'🔄 Renegociações feitas: {total_renegociacoes}')
    print(f'📋 Parcelas criadas: {total_parcelas}')
    print('=' * 50)
    print('\n🚀 Agora execute: flask run')
