# SGM - Backend

API do Sistema de Gerenciamento de Mercearia, desenvolvida em Flask.

## Acesso em produção

| Serviço | Link |
|---------|------|
| API (Swagger) | https://sgm-backend-8ft1.onrender.com/docs/ |

## Requisitos

- Python 3.9+

## Como rodar localmente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

A API estará disponível em **http://localhost:5001**

> O backend precisa estar rodando antes de iniciar o frontend.

## Login padrão

| Usuário | Senha |
|---------|-------|
| adm     | adm   |

## Endpoints

A documentação completa dos endpoints está disponível em **http://localhost:5001/docs/**

## Tecnologias e serviços

- [Flask](https://flask.palletsprojects.com/) — framework web
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) — ORM para banco de dados
- [Flasgger](https://github.com/flasgger/flasgger) — Swagger UI para documentação da API
- [SQLite](https://www.sqlite.org/) — banco de dados local (desenvolvimento)
- [PostgreSQL](https://www.postgresql.org/) via [Supabase](https://supabase.com) — banco de dados em produção
- [Gunicorn](https://gunicorn.org/) — servidor de produção
- [Render](https://render.com) — hospedagem do backend
