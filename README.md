# SGM - Backend

API do Sistema de Gerenciamento de Mercearia, desenvolvida em Flask + SQLite.

## Requisitos

- Python 3.9+

## Instalação

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Como rodar

```bash
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

## Tecnologias

- [Flask](https://flask.palletsprojects.com/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- [Flasgger](https://github.com/flasgger/flasgger) (Swagger UI)
- SQLite
