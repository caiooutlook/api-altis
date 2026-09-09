# Assistente Intelbras - Agente Multi-Agente com IA

## Arquitetura, Fluxo de Dados e Caminho para Produção com Azure

---

## 1. O que o Agente faz

O Assistente Intelbras é um chatbot com inteligência artificial que permite aos funcionários consultar, em linguagem natural, duas fontes de informação distintas:

**Documentação técnica de produtos**
- Especificações, manuais de instalação, procedimentos de configuração
- Resolução de problemas (troubleshooting)
- Guias operacionais (runbooks)

**Dados operacionais de negócio**
- Vendas por período, loja, produto ou vendedor
- Disponibilidade e estoque em cada loja
- Informações de funcionários e lojas

O agente **identifica automaticamente** o tipo de pergunta e aciona o sub-agente especializado correto, sem que o usuário precise escolher.

---

## 2. Arquitetura da POC

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USUÁRIO                                        │
│                      (Interface CLI)                                      │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ pergunta em linguagem natural
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AGENTE ORQUESTRADOR                                    │
│                       (LangGraph)                                         │
│                                                                           │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────────────────┐  │
│  │  Classificar  │──▶│    Rotear     │──▶│  Consolidar Resposta      │  │
│  │   Intenção    │   │  Sub-Agente   │   │  (texto final ao usuário) │  │
│  └───────────────┘   └───────────────┘   └───────────────────────────┘  │
└──────────┬───────────────────────────────────────────┬──────────────────┘
           │                                           │
           │ intent="rag"                              │ intent="sql"
           ▼                                           ▼
┌─────────────────────────┐              ┌──────────────────────────────┐
│     AGENTE RAG          │              │       AGENTE SQL             │
│                         │              │                              │
│ 1. Busca vetorial no    │              │ 1. LLM gera query SQL        │
│    ChromaDB (embeddings)│              │ 2. Valida segurança (SELECT) │
│ 2. Recupera documentos  │              │ 3. Executa no banco H2       │
│    relevantes           │              │ 4. LLM interpreta resultados │
│ 3. LLM gera resposta   │              │                              │
│    com citações         │              │                              │
└────────────┬────────────┘              └──────────────┬───────────────┘
             │                                          │
             ▼                                          ▼
┌─────────────────────────┐              ┌──────────────────────────────┐
│       ChromaDB          │              │      H2 Database             │
│   (Vector Store local)  │              │      (SQL embedded)          │
└────────────┬────────────┘              │                              │
             │                           │  - lojas (8)                 │
             ▼                           │  - funcionarios (15)         │
┌─────────────────────────┐              │  - produtos (15)             │
│   OKF Knowledge Base    │              │  - estoque (68)              │
│   (Markdown + YAML)     │              │  - vendas (51)               │
│                         │              └──────────────────────────────┘
│  - 8 docs de produtos   │
│  - 6 docs de schema BD  │
│  - 1 runbook            │
└─────────────────────────┘
```

---

## 3. Fluxo de Dados Detalhado

### Passo a Passo: Da Pergunta à Resposta

```
 USUÁRIO                ORQUESTRADOR              SUB-AGENTES              DADOS
    │                       │                         │                      │
    │  "Quantas VIP 1230    │                         │                      │
    │   foram vendidas?"    │                         │                      │
    │──────────────────────▶│                         │                      │
    │                       │                         │                      │
    │                       │ ┌─────────────────────┐ │                      │
    │                       │ │ CLASSIFICAÇÃO       │ │                      │
    │                       │ │ LLM analisa texto   │ │                      │
    │                       │ │ → intent = "sql"    │ │                      │
    │                       │ └─────────────────────┘ │                      │
    │                       │                         │                      │
    │                       │──── roteia para SQL ───▶│                      │
    │                       │                         │                      │
    │                       │                         │ ┌──────────────────┐ │
    │                       │                         │ │ GERAR SQL        │ │
    │                       │                         │ │ LLM + schema +   │ │
    │                       │                         │ │ few-shot examples│ │
    │                       │                         │ │ → SELECT SUM(...)│ │
    │                       │                         │ └──────────────────┘ │
    │                       │                         │                      │
    │                       │                         │ ┌──────────────────┐ │
    │                       │                         │ │ VALIDAR SQL      │ │
    │                       │                         │ │ • Somente SELECT │ │
    │                       │                         │ │ • Sem DROP/DELETE │ │
    │                       │                         │ └──────────────────┘ │
    │                       │                         │                      │
    │                       │                         │──── executa query ──▶│
    │                       │                         │                      │
    │                       │                         │◀──── resultados ─────│
    │                       │                         │                      │
    │                       │                         │ ┌──────────────────┐ │
    │                       │                         │ │ INTERPRETAR      │ │
    │                       │                         │ │ LLM transforma   │ │
    │                       │                         │ │ tabela em texto  │ │
    │                       │                         │ │ legível          │ │
    │                       │                         │ └──────────────────┘ │
    │                       │                         │                      │
    │                       │◀── resposta formatada ──│                      │
    │                       │                         │                      │
    │◀─────────────────────│                         │                      │
    │  "Foram vendidas 56   │                         │                      │
    │   unidades da VIP     │                         │                      │
    │   1230 D no Q1 2025"  │                         │                      │
    │                       │                         │                      │
```

### Fluxo RAG (Documentação Técnica)

```
 PERGUNTA: "Como configurar o mesh do Wi-Force?"
      │
      ▼
 ┌─────────────────────┐
 │ 1. EMBEDDING        │   Transforma a pergunta em vetor numérico
 │    (OpenAI API)     │   [0.012, -0.034, 0.089, ...]
 └──────────┬──────────┘
            │
            ▼
 ┌─────────────────────┐
 │ 2. BUSCA VETORIAL   │   Encontra os 4 chunks mais similares
 │    (ChromaDB)       │   no índice de documentos OKF
 └──────────┬──────────┘
            │
            ▼
 ┌─────────────────────┐
 │ 3. MONTAGEM DO      │   "Usando APENAS este contexto, responda:"
 │    CONTEXTO         │   [chunk1: seção mesh do wi-force...]
 │                     │   [chunk2: posicionamento de nós...]
 └──────────┬──────────┘
            │
            ▼
 ┌─────────────────────┐
 │ 4. GERAÇÃO          │   LLM gera resposta fiel ao contexto
 │    (GPT-4o/Claude)  │   com citações do documento fonte
 └──────────┬──────────┘
            │
            ▼
 RESPOSTA com instruções passo-a-passo extraídas da documentação
```

---

## 4. O Papel do OKF (Open Knowledge Format)

O OKF é o formato usado para organizar toda a documentação técnica que alimenta o agente RAG.

### Estrutura de um documento OKF

```yaml
---
type: product                           # Tipo: product, dataset, runbook
display_name: "Wi-Force W6 1500"        # Nome para exibição
tags: [roteador, wifi6, mesh]           # Tags para filtragem
category: Redes                         # Categoria
lifecycle: active                       # active | deprecated | draft
verified: human-reviewed                # Nível de confiança
sources:                                # Proveniência
  - uri: "https://intelbras.com/..."
    type: documentation
---

# Conteúdo em Markdown
(especificações, procedimentos, troubleshooting)
```

### Por que OKF?

| Benefício | Descrição |
|-----------|-----------|
| Legível por humanos | Markdown puro, sem ferramentas especiais |
| Versionável | Git diff, PR reviews, histórico completo |
| Metadata estruturada | YAML frontmatter permite filtragem e trust signals |
| Proveniência | Cada documento diz de onde veio e quem validou |
| Lifecycle | Documentos obsoletos são automaticamente rebaixados |
| Vendor-neutral | Funciona com qualquer LLM, vector store ou framework |

### Documentos OKF criados nesta POC

| Pasta | Documentos | Conteúdo |
|-------|------------|----------|
| `produtos/cameras/` | 2 | VIP 1230 D, VIP 3230 B |
| `produtos/redes/` | 2 | Wi-Force W6 1500, AP 1350 AC |
| `produtos/gravadores/` | 1 | MHDX 1004-C |
| `produtos/alarmes/` | 1 | AMT 8000 |
| `produtos/controle-acesso/` | 1 | ELC 5001 RF |
| `produtos/comunicacao/` | 1 | TIP 125i |
| `dados/` | 6 | Schemas do BD + modelo relacional |
| `runbooks/` | 1 | Acesso remoto DVR |

---

## 5. Tecnologias da POC vs. Produção com Azure

### Mapeamento direto de cada componente

```
┌────────────────────────┬──────────────────────┬────────────────────────────────┐
│      COMPONENTE        │       POC            │       PRODUÇÃO (AZURE)         │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Interface do usuário   │ CLI (terminal)       │ Microsoft Teams                │
│                        │                      │ (via Bot Framework)            │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ LLM                    │ OpenAI API /         │ Azure OpenAI Service           │
│                        │ Anthropic API        │ (GPT-4o no tenant corporativo) │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Orquestração           │ LangGraph            │ Azure AI Foundry Agent Service │
│                        │ (Python local)       │ ou LangGraph em Container Apps │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Embeddings             │ OpenAI API           │ Azure OpenAI Embeddings        │
│                        │ text-embedding-3     │ (mesmo modelo, endpoint Azure) │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Vector Store           │ ChromaDB (local)     │ Azure AI Search                │
│                        │                      │ (busca híbrida vetorial+BM25)  │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Banco de Dados         │ H2 (embedded)        │ Azure SQL Database             │
│                        │                      │ ou Azure PostgreSQL            │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Knowledge Base         │ OKF (arquivos        │ OKF em Azure DevOps Repos      │
│                        │ locais)              │ + pipeline CI/CD de ingestão   │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Autenticação           │ Nenhuma              │ Microsoft Entra ID (SSO)       │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Hospedagem             │ Máquina local        │ Azure Container Apps           │
│                        │                      │ ou Azure Kubernetes Service    │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Observabilidade        │ Print/console        │ Azure Monitor +                │
│                        │                      │ Application Insights           │
├────────────────────────┼──────────────────────┼────────────────────────────────┤
│ Segurança de dados     │ Arquivo local        │ Azure Key Vault (secrets)      │
│                        │                      │ + Private Endpoints            │
└────────────────────────┴──────────────────────┴────────────────────────────────┘
```

---

## 6. Arquitetura de Produção em Azure com Teams AI Library

### Entendendo as 3 camadas

Na produção com Teams, existem 3 camadas de software que trabalham juntas:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MICROSOFT TEAMS                                       │
│                  (interface do funcionário)                                   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ mensagem de chat
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AZURE BOT SERVICE  (recurso no Azure Portal — NÃO TEM CÓDIGO)              │
│                                                                              │
│  O que faz:                                                                  │
│  • Roteia mensagens entre o Teams e o seu servidor                           │
│  • Gerencia credenciais de autenticação do bot                               │
│  • Faz um HTTP POST para o endpoint configurado                              │
│                                                                              │
│  Configuração única:                                                         │
│  → Messaging endpoint: https://intelbras-bot.azurecontainerapps.io/api/msg  │
│  → Channel: Microsoft Teams (habilitado)                                     │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ HTTP POST /api/messages (JSON)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SEU CÓDIGO PYTHON  (hospedado em Azure Container Apps / App Service)        │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  TEAMS AI LIBRARY  (pip install teams-ai)                              │  │
│  │                                                                         │  │
│  │  O que faz:                                                             │  │
│  │  • Recebe a mensagem do Bot Service (usa Bot Framework SDK por baixo)  │  │
│  │  • Envia para o LLM (Azure OpenAI) com as actions/tools disponíveis    │  │
│  │  • O LLM DECIDE qual action chamar (substitui o orquestrador manual)  │  │
│  │  • Executa a action escolhida                                          │  │
│  │  • Retorna a resposta formatada para o Teams                           │  │
│  │  • Gerencia memória de conversa, streaming, Adaptive Cards             │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │  SUAS ACTIONS (funções Python — sua lógica de negócio)                 │  │
│  │                                                                         │  │
│  │  • buscar_documentacao() → chama Azure AI Search                       │  │
│  │  • consultar_dados()     → conecta no Azure SQL                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### O que é cada componente

| Componente | O que é | Onde roda | Você escreve código? |
|------------|---------|-----------|---------------------|
| **Azure Bot Service** | Recurso de infraestrutura no Azure Portal | Azure (gerenciado) | **Não.** Só configura o endpoint |
| **Bot Framework SDK** | Biblioteca Python de transporte (recebe/envia mensagens) | Dentro do seu app | Não diretamente — a Teams AI Library usa por baixo |
| **Teams AI Library** | Biblioteca Python de alto nível que gerencia o loop LLM + tools | Dentro do seu app | **Sim.** Você configura e registra actions |
| **Suas Actions** | Funções Python com a lógica de negócio | Dentro do seu app | **Sim.** Aqui fica o código de RAG e SQL |

### Diferença crucial: POC vs. Produção

Na POC, o **LangGraph** é quem classifica a intenção e roteia para o sub-agente correto. Na produção com Teams AI Library, **o próprio LLM (GPT-4o) faz esse papel** através do mecanismo de tool-calling:

```
 POC (LangGraph):                    PRODUÇÃO (Teams AI Library):

 pergunta                            pergunta
    │                                   │
    ▼                                   ▼
 ┌────────────────┐                  ┌────────────────────────────────┐
 │ LLM classifica │                  │ LLM recebe a lista de actions  │
 │ intent         │                  │ com suas descrições e DECIDE   │
 │ → "rag"/"sql"  │                  │ qual chamar baseado na         │
 └───────┬────────┘                  │ pergunta                       │
         │                           └───────┬────────────────────────┘
         ▼                                   │
 ┌────────────────┐                          │ tool_call: "consultar_dados"
 │ if/else roteia │                          │ arguments: {"pergunta": "..."}
 │ para sub-agente│                          ▼
 └────────────────┘                  ┌────────────────────────────────┐
                                     │ Teams AI Library executa a     │
                                     │ action correspondente          │
                                     └────────────────────────────────┘

 RESULTADO: Mesmo comportamento, menos código.
 O LLM é o orquestrador — não precisa de LangGraph.
```

---

## 7. Fluxo Detalhado com Teams AI Library e Actions

### Diagrama completo de infraestrutura

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MICROSOFT TEAMS                                        │
│                  (canal de entrada dos funcionários)                              │
└──────────────────────────────┬──────────────────────────────────────────────────┘
                               │ SSO via Entra ID (automático)
                               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        AZURE BOT SERVICE (infraestrutura)                         │
│                    roteia mensagens → seu endpoint HTTP                           │
└──────────────────────────────┬───────────────────────────────────────────────────┘
                               │ POST /api/messages
                               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        AZURE CONTAINER APPS                                       │
│                (hospeda seu código Python)                                        │
│                                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────┐    │
│  │                  TEAMS AI LIBRARY (loop principal)                         │    │
│  │                                                                            │    │
│  │  1. Recebe mensagem do funcionário                                        │    │
│  │  2. Envia para Azure OpenAI GPT-4o com system prompt + tools:             │    │
│  │     ┌────────────────────────────────────────────────────────────┐        │    │
│  │     │ tools: [                                                    │        │    │
│  │     │   {name: "buscar_documentacao",                             │        │    │
│  │     │    description: "Busca specs, configuração e troubleshoot"} │        │    │
│  │     │   {name: "consultar_dados",                                 │        │    │
│  │     │    description: "Consulta vendas, estoque, funcionários"}   │        │    │
│  │     │ ]                                                           │        │    │
│  │     └────────────────────────────────────────────────────────────┘        │    │
│  │  3. GPT-4o DECIDE qual tool chamar (ou ambas, ou nenhuma)                 │    │
│  │  4. Teams AI Library executa a action correspondente                      │    │
│  │  5. Resultado da action volta pro GPT-4o                                  │    │
│  │  6. GPT-4o formula resposta final em linguagem natural                    │    │
│  │  7. Resposta é enviada de volta ao Teams (com streaming)                  │    │
│  └────────────┬───────────────────────────────────────┬──────────────────────┘    │
│               │                                       │                           │
│               ▼                                       ▼                           │
│  ┌──────────────────────────┐         ┌────────────────────────────────────┐     │
│  │ ACTION: buscar_docs()    │         │ ACTION: consultar_dados()          │     │
│  │                          │         │                                    │     │
│  │ Sua função Python que:   │         │ Sua função Python que:             │     │
│  │ • Chama Azure AI Search  │         │ • Gera SQL (via LLM ou template)  │     │
│  │ • Faz busca vetorial     │         │ • Valida (somente SELECT)          │     │
│  │ • Retorna chunks         │         │ • Executa no Azure SQL             │     │
│  │   relevantes como texto  │         │ • Retorna resultados formatados    │     │
│  └────────────┬─────────────┘         └──────────────────┬─────────────────┘     │
└───────────────┼──────────────────────────────────────────┼───────────────────────┘
                │                                          │
                ▼                                          ▼
┌──────────────────────────────┐          ┌──────────────────────────────────────┐
│      AZURE AI SEARCH         │          │         AZURE SQL DATABASE           │
│                              │          │                                      │
│  • Índice vetorial           │          │  • lojas, funcionarios, produtos     │
│  • Busca híbrida (BM25+vec) │          │  • estoque, vendas                   │
│  • Filtros por metadata OKF  │          │  • Managed Identity (sem senha)      │
└──────────────┬───────────────┘          └──────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐          ┌──────────────────────────────────────┐
│  AZURE DEVOPS REPOS (Git)    │          │      AZURE KEY VAULT                 │
│                              │          │                                      │
│  • OKF Knowledge Bundle     │          │  • Connection strings                │
│  • CI/CD: ao fazer push,    │          │  • Certificados                      │
│    pipeline re-indexa no     │          │                                      │
│    Azure AI Search           │          │                                      │
└──────────────────────────────┘          └──────────────────────────────────────┘
```

### Como fica o código Python (app.py)

O código abaixo mostra a estrutura real da aplicação em produção:

```python
# app.py — Aplicação completa com Teams AI Library

from teams import Application, TurnState
from teams.ai import AIOptions
from teams.ai.models import AzureOpenAIModel
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from azure.identity import DefaultAzureCredential
import pyodbc

# ═══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════

# LLM (Azure OpenAI — dados ficam no tenant corporativo)
model = AzureOpenAIModel(
    azure_endpoint="https://intelbras-openai.openai.azure.com/",
    api_version="2024-06-01",
    model_deployment="gpt-4o"
)

# Vector Store (Azure AI Search)
search_client = SearchClient(
    endpoint="https://intelbras-search.search.windows.net",
    index_name="knowledge-intelbras",
    credential=DefaultAzureCredential()  # sem API key no código!
)

# Banco SQL (Azure SQL Database)
sql_conn_str = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=intelbras-sql.database.windows.net;"
    "Database=intelbras_vendas;"
    "Authentication=ActiveDirectoryMsi;"  # sem senha no código!
)

# ═══════════════════════════════════════════════════════════════════
# APLICAÇÃO TEAMS AI LIBRARY
# ═══════════════════════════════════════════════════════════════════

app = Application[TurnState](
    ai=AIOptions(model=model)
)

# ═══════════════════════════════════════════════════════════════════
# ACTION 1: Buscar na documentação técnica (RAG)
#
# A Teams AI Library registra essa função como "tool" disponível
# para o GPT-4o. O LLM decide quando chamar baseado na descrição.
# ═══════════════════════════════════════════════════════════════════

@app.ai.action("buscar_documentacao")
async def buscar_documentacao(context, state, parameters):
    """Busca informações técnicas sobre produtos Intelbras.
    Use para: especificações, configuração, instalação,
    troubleshooting, procedimentos operacionais."""

    query = parameters["pergunta"]

    # Faz busca vetorial + semântica no Azure AI Search
    results = search_client.search(
        search_text=query,
        vector_queries=[
            VectorizableTextQuery(
                text=query,
                k_nearest_neighbors=4,
                fields="content_vector"
            )
        ],
        select=["content", "title", "category", "source_path"]
    )

    # Monta o contexto com os documentos encontrados
    docs = []
    for result in results:
        docs.append(f"[Fonte: {result['title']}]\n{result['content']}")

    if not docs:
        return "Nenhum documento relevante encontrado na base de conhecimento."

    return "\n\n---\n\n".join(docs[:4])


# ═══════════════════════════════════════════════════════════════════
# ACTION 2: Consultar dados operacionais (SQL)
#
# O LLM chama esta action quando a pergunta envolve vendas,
# estoque, funcionários, lojas ou preços.
# ═══════════════════════════════════════════════════════════════════

SCHEMA_CONTEXT = """Tabelas: lojas(id,nome,cidade,estado,regiao),
funcionarios(id,nome,cargo,loja_id,email,salario),
produtos(id,codigo,nome,categoria,preco_unitario),
estoque(produto_id,loja_id,quantidade),
vendas(produto_id,loja_id,funcionario_id,quantidade,valor_total,data_venda)
Dados de vendas: Jan-Mar 2025. Use apenas SELECT."""

@app.ai.action("consultar_dados")
async def consultar_dados(context, state, parameters):
    """Consulta dados de vendas, estoque, disponibilidade,
    funcionários e lojas do banco de dados Intelbras.
    Use para: faturamento, quantidades vendidas, rankings,
    estoque disponível, informações de lojas."""

    pergunta = parameters["pergunta"]
    sql_query = parameters.get("sql_query", "")

    # Se o LLM não gerou o SQL diretamente, gera aqui
    if not sql_query:
        # Pede ao LLM que gere o SQL
        # (pode usar uma chamada separada ao Azure OpenAI)
        sql_query = await gerar_sql_com_llm(pergunta, SCHEMA_CONTEXT)

    # Validação de segurança
    if not sql_query.strip().upper().startswith("SELECT"):
        return "Erro: apenas consultas SELECT são permitidas."

    # Executa no Azure SQL
    try:
        with pyodbc.connect(sql_conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchmany(50)

        # Formata resultado
        header = " | ".join(columns)
        lines = [" | ".join(str(v) for v in row) for row in rows]
        resultado = f"{header}\n{'─' * len(header)}\n" + "\n".join(lines)

        return f"SQL executado: {sql_query}\n\nResultado:\n{resultado}"

    except Exception as e:
        return f"Erro ao consultar banco: {str(e)}"


# ═══════════════════════════════════════════════════════════════════
# O QUE ACONTECE AUTOMATICAMENTE (sem código seu):
#
# 1. Funcionário digita no Teams
# 2. Azure Bot Service envia para /api/messages
# 3. Teams AI Library recebe e monta o prompt:
#    - System prompt (comportamento do assistente)
#    - Tools disponíveis (buscar_documentacao, consultar_dados)
#    - Histórico da conversa (memória)
#    - Mensagem do usuário
# 4. GPT-4o analisa e decide:
#    - Chamar buscar_documentacao? consultar_dados? ambos? nenhum?
# 5. Se chamou uma action: executa e envia resultado de volta ao GPT-4o
# 6. GPT-4o formula a resposta final em linguagem natural
# 7. Teams AI Library envia de volta ao Teams (com streaming)
# ═══════════════════════════════════════════════════════════════════
```

### Fluxo passo a passo no Teams (com Actions)

```
 FUNCIONÁRIO                TEAMS AI LIBRARY              AZURE OpenAI (GPT-4o)
     │                           │                              │
     │ "Qual câmera tem WDR     │                              │
     │  e quanto vendemos dela?" │                              │
     │──────────────────────────▶│                              │
     │                           │                              │
     │                           │  Envia ao LLM:              │
     │                           │  • system prompt             │
     │                           │  • tools disponíveis         │
     │                           │  • mensagem do user          │
     │                           │─────────────────────────────▶│
     │                           │                              │
     │                           │                              │ GPT-4o decide:
     │                           │                              │ "Preciso chamar
     │                           │                              │  DUAS actions"
     │                           │                              │
     │                           │◀─────────────────────────────│
     │                           │  tool_call: buscar_docs      │
     │                           │  args: {pergunta: "câmera    │
     │                           │         com WDR"}            │
     │                           │                              │
     │                           │ Executa buscar_docs()        │
     │                           │ → Azure AI Search            │
     │                           │ → retorna: "VIP 3230 B      │
     │                           │   tem WDR real 120dB..."     │
     │                           │                              │
     │                           │  tool_call: consultar_dados  │
     │                           │  args: {pergunta: "vendas    │
     │                           │         VIP 3230 B"}         │
     │                           │                              │
     │                           │ Executa consultar_dados()    │
     │                           │ → Azure SQL                  │
     │                           │ → retorna: "12 unidades,     │
     │                           │   R$ 8.758,80 total"         │
     │                           │                              │
     │                           │  Envia resultados ao LLM:   │
     │                           │  • resultado action 1        │
     │                           │  • resultado action 2        │
     │                           │─────────────────────────────▶│
     │                           │                              │
     │                           │                              │ GPT-4o combina
     │                           │                              │ e formula resposta
     │                           │                              │ final em português
     │                           │                              │
     │                           │◀─────────────────────────────│
     │                           │  "A VIP 3230 B é a câmera    │
     │                           │   com WDR real (120dB).      │
     │                           │   Vendemos 12 unidades no    │
     │                           │   Q1 2025, totalizando       │
     │                           │   R$ 8.758,80..."            │
     │                           │                              │
     │◀──────────────────────────│                              │
     │  Resposta no chat Teams   │                              │
     │  (com streaming)          │                              │
```

### Como o banco vetorial é criado e populado

A Teams AI Library **não** cria o índice vetorial — isso é um setup separado. O índice vive no **Azure AI Search** e é populado por um pipeline de ingestão:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE DE INGESTÃO (roda no CI/CD)                    │
│                                                                           │
│   ┌──────────────┐     ┌──────────────┐     ┌───────────────────────┐   │
│   │ OKF Docs     │────▶│  Chunking    │────▶│ Azure OpenAI          │   │
│   │ (Git repo)   │     │ (divide em   │     │ Embeddings            │   │
│   │              │     │  pedaços de  │     │ (text-embedding-3)    │   │
│   │ cameras/     │     │  ~1000 chars)│     │ → gera vetores        │   │
│   │ redes/       │     │              │     │   [0.012, -0.03, ...] │   │
│   │ alarmes/     │     └──────────────┘     └───────────┬───────────┘   │
│   └──────────────┘                                      │               │
│                                                         ▼               │
│                                              ┌───────────────────────┐   │
│                                              │ Azure AI Search       │   │
│                                              │ (indexa texto +       │   │
│                                              │  vetor + metadata)    │   │
│                                              └───────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘

 Duas formas de criar o índice:

 1. VIA CÓDIGO (script Python no CI/CD — similar à POC):
    - Lê os .md do OKF
    - Faz chunking
    - Gera embeddings via Azure OpenAI
    - Upload para Azure AI Search via SDK Python

 2. VIA PORTAL (sem código):
    - Azure AI Search → "Import and vectorize data"
    - Aponta para Blob Storage onde estão os OKFs
    - O serviço faz tudo automaticamente
    - Configura um "skillset" que re-indexa quando há mudanças
```

### Como o banco SQL é acessado

A Teams AI Library **não** tem conector SQL embutido. Você usa qualquer cliente SQL dentro da sua action:

```
 Dentro da action "consultar_dados":

 ┌────────────────────────────────────────────────────────────────────┐
 │                                                                    │
 │  1. Recebe a pergunta em linguagem natural                        │
 │     "Quantas câmeras vendemos em março?"                          │
 │                                                                    │
 │  2. Gera SQL (via LLM com schema como contexto)                   │
 │     SELECT p.nome, SUM(v.quantidade) FROM vendas v                │
 │     JOIN produtos p ON ... WHERE MONTH(data_venda)=3              │
 │                                                                    │
 │  3. Valida segurança (só SELECT, sem DROP/DELETE/etc)              │
 │                                                                    │
 │  4. Conecta ao Azure SQL via pyodbc (com Managed Identity)        │
 │     → sem senha no código, autenticação automática               │
 │                                                                    │
 │  5. Executa a query e retorna resultados como texto               │
 │     "VIP 1230 D: 21 unidades | VIP 3230 B: 7 unidades | ..."     │
 │                                                                    │
 │  6. A Teams AI Library devolve esse texto ao GPT-4o               │
 │     → GPT-4o formula resposta natural para o funcionário         │
 │                                                                    │
 └────────────────────────────────────────────────────────────────────┘
```

---

## 8. Integração com Microsoft Teams — Detalhamento

### O que cada componente faz na prática

```
┌─────────────────────────────────────────────────────────────────────────┐
│ AZURE BOT SERVICE                                                        │
│                                                                          │
│ • É um RECURSO no Azure Portal (não é um servidor, não tem código)      │
│ • Funciona como um "carteiro": recebe mensagem do Teams e                │
│   faz um HTTP POST para o seu endpoint                                   │
│ • Configuração única: App ID + Password + Messaging Endpoint             │
│ • Você NÃO escreve código nele                                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ BOT FRAMEWORK SDK  (pip install botbuilder-core)                         │
│                                                                          │
│ • Biblioteca de BAIXO NÍVEL                                              │
│ • Recebe o JSON do Bot Service, deserializa, autentica                   │
│ • Você NÃO usa diretamente — a Teams AI Library encapsula               │
│ • Equivalente a: Flask é para HTTP assim como Bot Framework é            │
│   para mensagens de bot                                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ TEAMS AI LIBRARY  (pip install teams-ai)                                 │
│                                                                          │
│ • Biblioteca de ALTO NÍVEL (usa Bot Framework por baixo)                 │
│ • É O ORQUESTRADOR — substitui o LangGraph da POC                       │
│ • Faz o loop completo:                                                   │
│   mensagem → LLM → tool calling → executa action → resposta            │
│ • Gerencia automaticamente:                                              │
│   - Memória de conversa (contexto entre mensagens)                      │
│   - Streaming de resposta (texto aparece gradualmente)                  │
│   - Adaptive Cards (respostas ricas com tabelas e botões)               │
│   - Moderação de conteúdo (filtra inputs inapropriados)                 │
│   - Feedback do usuário (thumbs up/down)                                │
│ • Você REGISTRA actions (funções Python) e ela cuida do resto           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ SUAS ACTIONS  (funções Python normais)                                   │
│                                                                          │
│ • São funções async Python que contêm sua lógica de negócio             │
│ • A Teams AI Library expõe elas como "tools" para o GPT-4o             │
│ • O GPT-4o decide qual chamar baseado na descrição da function          │
│ • Dentro, você faz o que quiser: chamar APIs, banco, buscar docs        │
│ • Equivalente exato aos sub-agentes RAG e SQL da POC                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Fluxo completo no Teams (resumo visual)

```
 1. Funcionário digita no chat do Teams:
    "Qual o estoque da câmera VIP 1230 D em Curitiba?"

 2. Teams → Azure Bot Service → POST HTTP → seu código Python

 3. Teams AI Library recebe e envia ao GPT-4o:
    "O usuário perguntou X. Você tem essas tools: [buscar_docs, consultar_dados]"

 4. GPT-4o responde: tool_call("consultar_dados", {pergunta: "estoque VIP 1230 D Curitiba"})

 5. Teams AI Library executa sua action consultar_dados()
    → sua função conecta no Azure SQL e retorna: "22 unidades"

 6. Teams AI Library envia resultado de volta ao GPT-4o
    GPT-4o formula: "A loja de Curitiba possui 22 unidades da VIP 1230 D em estoque."

 7. Resposta aparece no Teams como Adaptive Card:
    ┌───────────────────────────────────────────┐
    │ 📦 Estoque: VIP 1230 D                    │
    │                                           │
    │ Loja Curitiba: 22 unidades                │
    │ Última atualização: 08/01/2025            │
    │                                           │
    │ [Ver em todas as lojas] [Detalhes produto]│
    └───────────────────────────────────────────┘
```

### Recursos que a Teams AI Library entrega "de graça"

| Recurso | Como funciona |
|---------|---------------|
| **Streaming** | Texto aparece letra a letra no chat (como ChatGPT) |
| **Memória** | Mantém contexto da conversa — follow-ups funcionam |
| **Multi-tool** | GPT-4o pode chamar DUAS actions na mesma pergunta |
| **Adaptive Cards** | Respostas ricas com tabelas, botões e ações |
| **Feedback** | Polegar cima/baixo em cada resposta |
| **Moderação** | Filtra conteúdo impróprio no input e output |
| **Auth SSO** | Sabe quem é o funcionário via Entra ID automaticamente |

### O que muda em relação à POC

| Aspecto | POC (hoje) | Produção (Teams AI Library) |
|---------|-----------|----------------------------|
| Interface | `input()` no terminal | Chat no Teams |
| Orquestrador | LangGraph (classify → route → respond) | Teams AI Library + GPT-4o tool-calling |
| Classificação | LLM + if/else manual | GPT-4o decide automaticamente pela descrição das actions |
| Lógica RAG | Sua função `rag_search()` | Mesma lógica, dentro de uma `@app.ai.action` |
| Lógica SQL | Sua função `sql_search()` | Mesma lógica, dentro de uma `@app.ai.action` |
| Memória | Nenhuma | Automática (Teams AI Library gerencia) |
| Deploy | `python -m src.main` | Container no Azure Container Apps |

---

## 9. Pipeline CI/CD para a Knowledge Base

```
┌──────────────┐    ┌───────────────┐    ┌──────────────────┐    ┌─────────────┐
│  Engenheiro  │───▶│  Pull Request │───▶│  Pipeline CI/CD  │───▶│ Azure AI    │
│  atualiza    │    │  (review do   │    │                  │    │ Search      │
│  doc OKF     │    │   conteúdo)   │    │ 1. Valida YAML   │    │ (re-indexa) │
│  no Git      │    │              │    │ 2. Gera chunks   │    │             │
└──────────────┘    └───────────────┘    │ 3. Cria embedd.  │    └─────────────┘
                                         │ 4. Atualiza índice│
                                         └──────────────────┘
```

Quando um engenheiro adiciona ou atualiza um documento OKF:
1. Faz commit no Azure DevOps Repos
2. Abre PR — outro engenheiro revisa o conteúdo técnico
3. Após merge na main, pipeline Azure DevOps dispara automaticamente
4. Pipeline valida frontmatter, faz chunking, gera embeddings e atualiza o índice
5. O agente passa a responder com o conteúdo atualizado — sem deploy

---

## 10. Segurança e Compliance

| Aspecto | Implementação Azure |
|---------|---------------------|
| Dados no tenant | Azure OpenAI roda no tenant da Intelbras — dados não saem para a OpenAI pública |
| Autenticação | Microsoft Entra ID — SSO corporativo, MFA |
| Autorização | RBAC baseado em grupo do AD — quem vê o quê |
| Secrets | Azure Key Vault com Managed Identity — sem senhas no código |
| Rede | Private Endpoints — banco e AI Search sem IP público |
| Auditoria | Logs em Azure Monitor — quem perguntou o quê e quando |
| Compliance | Dados em região Brasil (Brazil South) se necessário |
| SQL Injection | Agente SQL só executa SELECT — validação antes de executar |

---

## 11. Estimativa de Esforço para Migração

| Fase | Atividade | Estimativa |
|------|-----------|------------|
| 1 | Provisionar infra Azure (Bicep/Terraform) | 1-2 semanas |
| 2 | Migrar banco H2 → Azure SQL + popular dados reais | 1 semana |
| 3 | Configurar Azure AI Search + pipeline de ingestão OKF | 1-2 semanas |
| 4 | Substituir OpenAI API → Azure OpenAI (mudança de endpoint) | 1-2 dias |
| 5 | Implementar Bot Framework + canal Teams | 2-3 semanas |
| 6 | Autenticação Entra ID + RBAC | 1 semana |
| 7 | Expandir knowledge base OKF com documentação real | contínuo |
| 8 | Testes, observabilidade, go-live | 1-2 semanas |
| **Total** | | **8-12 semanas** |

---

## 12. Resumo Executivo

| Item | Valor |
|------|-------|
| **O que é** | Chatbot IA para consultas internas da Intelbras |
| **Quem usa** | Funcionários (vendedores, técnicos, gerentes) |
| **O que responde** | Documentação técnica + dados de vendas/estoque |
| **Como funciona** | Agente classifica a pergunta e roteia para RAG ou SQL |
| **Base de conhecimento** | OKF (Markdown + YAML) — versionável, auditável |
| **LLM** | Azure OpenAI GPT-4o (dados no tenant corporativo) |
| **Canal** | Microsoft Teams (SSO, sem app adicional) |
| **Infraestrutura** | 100% Azure (Container Apps, AI Search, SQL, Bot Service) |
| **Segurança** | Entra ID + Private Endpoints + Key Vault + RBAC |
