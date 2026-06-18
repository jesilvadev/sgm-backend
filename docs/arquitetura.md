# Arquitetura do Sistema – SGM (Sistema de Gestão de Dívidas da Mercearia)

## 1. Visão Geral

O SGM (Sistema de Gestão de Dívidas da Mercearia) é um sistema web desenvolvido para auxiliar no controle de clientes, dívidas, pagamentos e relatórios financeiros de uma mercearia. O sistema permite o gerenciamento eficiente das informações financeiras, organização e facilidade de uso.

A arquitetura foi planejada em nível introdutório, conforme proposto pela disciplina de Engenharia de Software, priorizando a separação de responsabilidades, clareza no fluxo do sistema e uso de tecnologias acessíveis.

---

## 2. Tecnologias Utilizadas

- **Back-end:** Python com Flask  
- **Front-end:** HTML
- **Banco de Dados:** SQLite  
- **Controle de Versão:** Git e GitHub  
- **Servidor de Desenvolvimento:** Flask local  

---

## 3. Separação de Responsabilidades

O sistema foi organizado em camadas, de forma a manter a separação entre:

- **Interface (Front-end):**
  - Responsável pela interação com o usuário.
  - Telas de login, cadastro, registro de dívidas, pagamentos e relatórios.

- **Lógica de Negócio (Back-end):**
  - Processamento dos dados.
  - Regras para criação, edição, renegociação e pagamento de dívidas.
  - Autenticação de usuários e controle de acessos.

- **Persistência de Dados (Banco de Dados):**
  - Armazena clientes, funcionários, dívidas, pagamentos e histórico financeiro.

Essa separação garante maior organização do código, facilidade de manutenção e melhor entendimento do sistema.

---

## 4. Fluxo Básico do Sistema

O funcionamento básico do sistema segue as seguintes etapas:

1. O usuário realiza o **login** no sistema.
2. O sistema valida as credenciais e libera o acesso conforme o tipo de usuário.
3. O usuário pode:
   - Cadastrar e buscar clientes;
   - Registrar novas vendas (dívidas);
   - Registrar pagamentos;
   - Editar, renegociar ou perdoar juros de dívidas;
   - Consultar extratos e saldo;
   - Visualizar relatórios e dashboards.
4. Todas as informações são armazenadas no banco de dados.
5. O sistema exibe os resultados atualizados para o usuário em tempo real.

---

## 5. Diagrama do Sistema

A arquitetura do sistema é representada por meio dos seguintes diagramas:

- **Diagrama de Casos de Uso:** Representa as funcionalidades disponíveis para os atores (Dono, Funcionário e Cliente).
- **Diagrama de Classes:** Representa a estrutura do sistema e o relacionamento entre suas entidades.
- **Diagrama Entidade-Relacionamento (DER)** Define as principais entidades e seus relacionamentos.

Esses diagramas estão disponíveis nesta mesma pasta (/docs) e foram utilizados como base para a implementação do sistema.

---

## 6. Organização Geral da Arquitetura

O sistema segue uma arquitetura em camadas:

- Camada de Apresentação (Front-end)
- Camada de Aplicação (Back-end)
- Camada de Dados (Banco de Dados)

Essa organização facilita a evolução do sistema e torna o projeto mais aderente às boas práticas de desenvolvimento de software.
