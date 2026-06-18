"""
SGM - Sistema de Gerenciamento de Mercearia
Aplicação Flask para controle de vendas fiado (a prazo)

Funcionalidades:
- Gerenciamento de clientes
- Registro de dívidas (vendas a prazo)
- Controle de pagamentos
- Renegociação de dívidas
- Dashboard com análises e relatórios
- Sistema de autenticação (Admin/Caixa)
"""

import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flasgger import Swagger

load_dotenv()
from web.models import db, Usuario
from werkzeug.security import generate_password_hash
from web.routes import register_routes

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: rule.rule.startswith("/api/"),
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/",
    "uiversion": 3,
    "swagger_ui_config": {
        "displayOperationId": False,
    },
    "info": {
        "title": "SGM - API",
        "description": "Endpoints JSON do Sistema de Gerenciamento de Mercearia",
        "version": "1.0.0",
    },
}


def create_app():
    """
    Factory function para criar e configurar a aplicação Flask
    
    Returns:
        Flask app configurada e pronta para uso
    """
    app = Flask(__name__)
    
    # Configurações do banco de dados
    # Em produção define DATABASE_URL no .env com a string do PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///sgm.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desativa warnings desnecessários
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'troque-esta-chave-por-uma-segura')
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = True

    # Inicializa o banco de dados
    db.init_app(app)

    # Habilita CORS para o React (porta 5173 padrão do Vite)
    CORS(app, resources={r"/api/*": {"origins": [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:5001",
        "https://sgm-gestao.web.app",
        "https://sgm-gestao.firebaseapp.com",
    ]}}, supports_credentials=True)

    # Registra todas as rotas da aplicação
    register_routes(app)

    # Inicializa o Swagger UI em /docs/
    Swagger(app, config=SWAGGER_CONFIG, merge=True)

    # Cria as tabelas e usuário admin padrão
    with app.app_context():
        db.create_all()
        
        # Cria usuário administrador padrão se não existir
        if not Usuario.query.filter_by(nome='adm').first():
            admin = Usuario(
                nome='adm',
                cpf=None,
                email='adm@sgm.com',
                senha_hash=generate_password_hash('adm', method='pbkdf2:sha256'),
                tipo='Administrador'
            )
            db.session.add(admin)
            db.session.commit()
            print("✓ Usuário administrador criado: adm/adm")

    return app


if __name__ == '__main__':
    # Cria e executa a aplicação
    app = create_app()
    print("\n" + "="*50)
    print("SGM - Sistema de Gerenciamento de Mercearia")
    print("="*50)
    print("➜ Acesse: http://127.0.0.1:5001")
    print("➜ Login padrão: adm / adm")
    print("➜ Swagger (API docs): http://127.0.0.1:5001/docs/")
    print("="*50 + "\n")
    app.run(debug=True, port=5001)
