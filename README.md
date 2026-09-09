# Intelbras Chatbot POC - Multi-Agente com LangGraph

POC de um chatbot multi-agente para funcionários da Intelbras. Combina busca em documentação técnica (RAG) com consultas a dados operacionais (SQL), orquestrado por um agente central usando LangGraph.

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    USUÁRIO (CLI)                          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│            AGENTE ORQUESTRADOR (LangGraph)                │
│         classifica intenção → roteia → consolida          │
└──────────┬──────────────────────┬───────────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐    ┌──────────────────┐
│   AGENTE RAG     │    │   AGENTE SQL     │
│  (Documentação)  │    │ (Banco de Dados) │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│    ChromaDB      │    │    H2 Database   │
│  (embeddings)    │    │  (vendas, lojas, │
│                  │    │   estoque, etc.) │
└────────┬─────────┘    └──────────────────┘
         │
         ▼
┌──────────────────┐
│  OKF Knowledge   │
│  Bundle (Markdown │
│  + YAML)         │
└──────────────────┘
```

## Stack Tecnológica

| Componente | Tecnologia |
|---|---|
| LLM | OpenAI (GPT-4o) ou Anthropic (Claude) |
| Orquestração | LangGraph |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | ChromaDB (local) |
| Banco de Dados | Microsoft SQL Server (via ODBC/pyodbc) |
| Knowledge Base | Open Knowledge Format (OKF) |
| Interface | CLI com Rich |
| Linguagem | Python 3.11+ |

## Pré-requisitos

- **Python 3.11+**
- **Microsoft SQL Server** acessível (local, container Docker ou Azure SQL)
- **ODBC Driver for SQL Server** (ex: "ODBC Driver 17 for SQL Server")
- **API Key** de pelo menos um provider: OpenAI ou Anthropic

Verifique os pré-requisitos:

```bash
python --version   # >= 3.11
```

> Para subir rapidamente um SQL Server local via Docker:
> ```bash
> docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=Your_password123" \
>   -p 1433:1433 -d mcr.microsoft.com/mssql/server:2022-latest
> ```

## Setup

### 1. Clone e entre no diretório

```bash
cd intelbras-chatbot-poc
```

### 2. Crie e ative um virtual environment

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` e configure pelo menos:

```env
# Escolha o provider
LLM_PROVIDER=openai

# Sua API key
OPENAI_API_KEY=sk-sua-chave-aqui

# Ou, para usar Claude:
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui

# Conexão com o SQL Server
SQLSERVER_HOST=localhost
SQLSERVER_PORT=1433
SQLSERVER_DATABASE=intelbras_db
SQLSERVER_USER=sa
SQLSERVER_PASSWORD=Your_password123
```

### 5. Inicialize o banco de dados

```bash
python scripts/init_database.py
```

Isso cria o banco (se necessário), as tabelas e insere dados de exemplo (8 lojas, 15 funcionários, 15 produtos, estoque e vendas de Jan-Mar 2025).

### 6. Indexe a base de conhecimento

```bash
python -m src.rag_agent
```

Isso processa os documentos OKF, gera embeddings e indexa no ChromaDB.

### 7. Execute o chatbot

```bash
python -m src.main
```

## Uso

Após iniciar, digite perguntas em linguagem natural:

### Perguntas sobre documentação (aciona o Agente RAG)
```
Você: Como configurar o mesh no roteador Wi-Force W6 1500?
Você: Qual a resolução da câmera VIP 3230 B?
Você: Como resetar a fechadura digital ELC 5001?
Você: O que é a detecção inteligente do DVR MHDX 1004-C?
```

### Perguntas sobre dados (aciona o Agente SQL)
```
Você: Quantas câmeras VIP 1230 D foram vendidas em janeiro?
Você: Qual loja vendeu mais em março de 2025?
Você: Qual o estoque do Wi-Force W6 1500 na loja de São Paulo?
Você: Quem são os gerentes de loja?
Você: Qual o faturamento total por categoria?
```

### Perguntas mistas (aciona ambos)
```
Você: O DVR MHDX 1004-C tem estoque? Como faço para configurar o acesso remoto?
```

### Comandos
- `/ajuda` — Mostra ajuda e exemplos
- `/debug` — Ativa modo debug (mostra intent e SQL gerado)
- `/modelo` — Mostra o modelo LLM em uso
- `/exemplos` — Lista perguntas de exemplo
- `/sair` — Encerra

## Estrutura do Projeto

```
intelbras-chatbot-poc/
├── .env.example              # Template de configuração
├── pyproject.toml            # Metadata do projeto
├── requirements.txt          # Dependências Python
├── README.md
│
├── scripts/
│   ├── download_h2.py        # Baixa o JAR do H2
│   └── init_database.py      # Cria tabelas e insere dados
│
├── src/
│   ├── __init__.py
│   ├── config.py             # Configuração centralizada
│   ├── llm.py               # Abstração OpenAI/Anthropic
│   ├── rag_agent.py          # Agente RAG (documentação)
│   ├── sql_agent.py          # Agente SQL (banco de dados)
│   ├── orchestrator.py       # Orquestrador LangGraph
│   └── main.py              # CLI interativa
│
├── knowledge/                # Base de conhecimento OKF
│   ├── okf.yaml             # Manifesto do bundle
│   ├── produtos/
│   │   ├── cameras/
│   │   │   ├── vip-1230-d.md
│   │   │   └── vip-3230-b.md
│   │   ├── redes/
│   │   │   ├── wi-force-w6-1500.md
│   │   │   └── ap-1350-ac.md
│   │   ├── gravadores/
│   │   │   └── mhdx-1004-c.md
│   │   ├── alarmes/
│   │   │   └── amt-8000.md
│   │   ├── controle-acesso/
│   │   │   └── elc-5001-rf.md
│   │   └── comunicacao/
│   │       └── tip-125i.md
│   └── runbooks/
│       └── configurar-acesso-remoto-dvr.md
│
├── data/                     # Dados gerados (gitignore)
│   ├── intelbras_db.*        # Arquivos do H2
│   └── chroma_db/            # Índice vetorial
│
└── lib/                      # JARs (gitignore)
    └── h2-2.2.224.jar
```

## Como funciona o OKF (Open Knowledge Format)

Os documentos de conhecimento seguem o formato [OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — arquivos Markdown com frontmatter YAML:

```markdown
---
type: product
display_name: "Câmera IP Dome VIP 1230 D"
description: "Câmera IP dome 2MP com IR inteligente"
tags: [camera, ip, dome, seguranca]
category: Câmeras
codigo: VIP-1230-D
lifecycle: active
verified: human-reviewed
sources:
  - uri: "https://www.intelbras.com/..."
    type: documentation
---

# Câmera IP Dome VIP 1230 D

## Especificações
...

## Configuração
...
```

Para adicionar novos produtos, crie um arquivo `.md` seguindo este formato na pasta `knowledge/produtos/<categoria>/`.

Após adicionar/modificar documentos, re-indexe:

```bash
python -m src.rag_agent
```

## Trocar entre OpenAI e Claude

No arquivo `.env`, altere:

```env
# Para OpenAI (GPT-4o)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Para Anthropic (Claude)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

Os embeddings sempre usam OpenAI (necessário manter `OPENAI_API_KEY` mesmo com Claude como LLM principal).

## Limitações da POC

- **H2 em modo embedded:** apenas uma conexão por vez (não é multi-user)
- **Sem histórico de conversa:** cada pergunta é independente (sem memória de contexto)
- **Sem autenticação:** qualquer pessoa com acesso pode consultar todos os dados
- **Base de conhecimento pequena:** 8 documentos de exemplo (expandir conforme necessário)
- **Sem streaming:** a resposta só aparece quando completa

## Próximos Passos (Produção)

1. **Migrar banco para Azure SQL / PostgreSQL** com connection pooling
2. **Adicionar memória de conversa** (LangGraph checkpointing ou Redis)
3. **Integrar com Microsoft Teams** via Bot Framework
4. **Autenticação** via Microsoft Entra ID (SSO corporativo)
5. **Expandir knowledge base** com todos os manuais reais
6. **Observabilidade** com LangSmith ou Application Insights
7. **Guardrails de segurança** (rate limiting, content filtering)
8. **CI/CD** para re-indexar automaticamente ao atualizar documentos OKF
