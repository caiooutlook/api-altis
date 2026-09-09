# Deploy da Arquitetura na Azure — Passo a Passo

Guia prático para subir o assistente multi-agente Intelbras na Azure usando o
**Azure AI Foundry Agent Service** como orquestrador, mantendo a mesma lógica da
POC:

- **Agente SQL**: lê o OKF/knowledge que descreve a estrutura do banco (schemas
  em `knowledge/dados/*.md`) para montar SQL e recuperar dados no **Azure SQL Database**.
- **Agente RAG**: usa uma **base de conhecimento (knowledge source)** no **Azure AI Search**
  alimentada por **PDFs** (datasheets, manuais) em um container do Blob Storage.

> Este guia complementa `docs/apresentacao-arquitetura.md` (mapeamento POC → Azure).
> Aqui o foco é o passo a passo operacional de provisionamento e configuração.

---

## Visão geral dos recursos Azure

| # | Recurso | Papel na arquitetura |
|---|---------|----------------------|
| 1 | Resource Group | Agrupa tudo em um só lugar |
| 2 | Azure OpenAI (via AI Foundry) | LLM (GPT-4o) + embeddings (text-embedding-3-small) |
| 3 | Azure AI Foundry (Hub + Project) | Onde o **agente** vive e é publicado |
| 4 | Azure AI Search | Vector store da base de PDFs (agente RAG) |
| 5 | Azure Storage (Blob) | Guarda os PDFs que alimentam o AI Search |
| 6 | Azure SQL Database | Banco operacional (agente SQL) |
| 7 | Azure Key Vault | Segredos (connection strings, chaves) |
| 8 | Azure Container Apps *(opcional)* | Hospeda um app/API próprio se você não usar só o Agent Service |
| 9 | Managed Identity | Autenticação sem senha entre os serviços |

O mapa mental da execução:

```
Usuário → Agente (AI Foundry Agent Service)
                │
                ├── tool "buscar_documentacao"  → Azure AI Search (índice dos PDFs)
                └── tool "consultar_dados"       → gera SQL (usa OKF de schema) → Azure SQL
```

---

## Pré-requisitos

- Assinatura Azure com permissão de **Owner/Contributor** no resource group.
- **Azure CLI** instalado e logado: `az login`.
- Acesso ao **Azure OpenAI** habilitado na assinatura (é um recurso com aprovação).
- Os PDFs de produtos prontos (datasheets/manuais) para a base do RAG.
- O banco já modelado pelo script `scripts/init_database.py` (tabelas + views + a
  tabela materializada `tb_ia_fonte_dados` para indexação, se for indexar dados de negócio).

Defina variáveis base (PowerShell) que usaremos no guia:

```powershell
$RG        = "rg-intelbras-ia"
$LOC       = "eastus2"
$PREFIX    = "intelbras"
az group create -n $RG -l $LOC
```

---

## Etapa 1 — Azure OpenAI (LLM + Embeddings)

O código usa `gpt-4o` para completions e `text-embedding-3-small` para embeddings.
Vamos provisionar os dois deployments.

```powershell
$AOAI = "$PREFIX-aoai"
az cognitiveservices account create `
  -n $AOAI -g $RG -l $LOC `
  --kind OpenAI --sku S0 `
  --custom-domain $AOAI

# Deployment do LLM
az cognitiveservices account deployment create `
  -n $AOAI -g $RG `
  --deployment-name gpt-4o `
  --model-name gpt-4o --model-version "2024-08-06" `
  --model-format OpenAI --sku-capacity 20 --sku-name Standard

# Deployment de embeddings
az cognitiveservices account deployment create `
  -n $AOAI -g $RG `
  --deployment-name text-embedding-3-small `
  --model-name text-embedding-3-small --model-version "1" `
  --model-format OpenAI --sku-capacity 50 --sku-name Standard
```

Anote o endpoint: `https://$AOAI.openai.azure.com/`.

> No código, isso substitui `OPENAI_API_KEY`/`OPENAI_MODEL`. Em produção, prefira
> o SDK `AzureOpenAI` (endpoint + `api_version`) em vez do `OpenAI` público. Veja
> a seção "Ajustes de código" no final.

---

## Etapa 2 — Azure SQL Database (agente SQL)

```powershell
$SQLSRV = "$PREFIX-sqlsrv"
$SQLDB  = "intelbras_db"
$SQLADM = "sqladmin"
$SQLPWD = "<uma-senha-forte>"

az sql server create -n $SQLSRV -g $RG -l $LOC -u $SQLADM -p $SQLPWD

# Libera acesso de serviços Azure (para POC). Em produção, use Private Endpoint.
az sql server firewall-rule create -g $RG -s $SQLSRV `
  -n AllowAzure --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0

az sql db create -g $RG -s $SQLSRV -n $SQLDB --service-objective S0
```

Popular o banco com o script da POC (ele já cria tabelas, views e a tabela
materializada `tb_ia_fonte_dados`):

```powershell
# No .env, aponte para o Azure SQL:
# SQLSERVER_HOST=intelbras-sqlsrv.database.windows.net
# SQLSERVER_PORT=1433
# SQLSERVER_DATABASE=intelbras_db
# SQLSERVER_USER=sqladmin
# SQLSERVER_PASSWORD=<senha>
# SQLSERVER_ENCRYPT=yes
# SQLSERVER_TRUST_CERT=no
python scripts/init_database.py
```

> O agente SQL **não** indexa o banco no AI Search por padrão — ele gera SQL e
> consulta ao vivo. A base de conhecimento que ele usa para montar o SQL é o
> **schema descrito em `knowledge/dados/*.md`** (veja Etapa 5).

---

## Etapa 3 — Storage + upload dos PDFs (fonte do RAG)

```powershell
$STG = "${PREFIX}stg$((Get-Random -Max 9999))"
az storage account create -n $STG -g $RG -l $LOC --sku Standard_LRS
$KEY = az storage account keys list -n $STG -g $RG --query "[0].value" -o tsv

az storage container create --account-name $STG --account-key $KEY -n produtos-pdfs

# Sobe os PDFs (ajuste o caminho local)
az storage blob upload-batch --account-name $STG --account-key $KEY `
  -d produtos-pdfs -s ".\pdfs"
```

---

## Etapa 4 — Azure AI Search + indexação dos PDFs (agente RAG)

Esta é a "base de conhecimento cadastrada" do agente RAG. O AI Search consegue
fazer **ingestão dos PDFs** (crack + chunk + embeddings) via a pipeline
"Import and vectorize data".

1. Crie o serviço:

```powershell
$SEARCH = "$PREFIX-search"
az search service create -n $SEARCH -g $RG -l $LOC --sku Standard
```

2. No **Azure portal → seu AI Search → Import and vectorize data**:
   - **Data source**: o container `produtos-pdfs` do Blob Storage.
   - **Vectorization**: escolha o deployment `text-embedding-3-small` do seu Azure OpenAI.
   - Isso cria automaticamente: **data source**, **skillset** (extração de texto +
     split em chunks + embeddings), **index** (com campo vetorial) e **indexer**.
   - Ative **schedule** para reindexar quando novos PDFs forem adicionados.

3. Alternativa por código: use o SDK `azure-search-documents` para criar índice
   com `SearchField` vetorial e um `SearchIndexer` apontando para o Blob. O
   equivalente ao que o `rag_agent.py` faz hoje com ChromaDB.

> Resultado: um índice pesquisável (ex.: `produtos-index`) que o agente RAG
> consulta por busca híbrida (vetorial + BM25).

---

## Etapa 5 — Conhecimento de schema para o agente SQL

O agente SQL precisa "entender" o banco para montar SQL. Hoje o `sql_agent.py`
tem o schema embutido em `DB_SCHEMA`. Na Azure você tem duas opções:

- **Opção A (simples, recomendada)**: manter o schema como **instrução do agente**.
  Concatene o conteúdo de `knowledge/dados/*.md` (modelo relacional + schemas de
  lojas, funcionários, produtos, estoque, vendas) no *system prompt / instructions*
  do agente, junto com as regras (somente SELECT, usar TOP em vez de LIMIT, datas
  em `YYYY-MM-DD`). É determinístico e barato.

- **Opção B**: indexar `knowledge/dados/*.md` em um **segundo índice** do AI Search
  e dar ao agente uma tool "buscar_schema" para recuperar só a parte relevante do
  schema antes de gerar o SQL. Vale a pena quando o schema é grande.

Para a POC atual (5 tabelas), a **Opção A** é suficiente.

---

## Etapa 6 — Criar o agente no AI Foundry

1. Crie o **Hub** e o **Project** do AI Foundry (portal `ai.azure.com` ou CLI/Bicep).
   Conecte o Azure OpenAI da Etapa 1 ao project.

2. No project, crie um **Agent** e configure:
   - **Model**: deployment `gpt-4o`.
   - **Instructions**: system prompt do orquestrador + schema (Etapa 5) + regras SQL.
   - **Tools**:
     - **Azure AI Search tool** → aponta para o índice `produtos-index` (Etapa 4).
       Substitui o `rag_agent.search()`.
     - **Function tool `consultar_dados(pergunta)`** → sua função que gera SQL a
       partir da pergunta + schema, valida (somente SELECT) e executa no Azure SQL.
       Reaproveita a lógica de `sql_agent.py` (`get_sql_prompt`, `validate_query`,
       `execute_query`).

3. O **roteamento** que hoje está no `orchestrator.py` (classify → rag/sql/both)
   passa a ser feito pelo **próprio modelo via tool-calling**: o LLM decide quando
   chamar a busca de documentação, quando consultar dados, ou ambos. Você não
   precisa mais do grafo LangGraph manual — as ferramentas cobrem os casos "rag",
   "sql" e "both".

> Se você preferir **manter o LangGraph**, pule o Agent Service e hospede o
> `orchestrator.py` num Azure Container App (Etapa 8), trocando apenas os clientes
> (Azure OpenAI, AI Search, Azure SQL). As duas abordagens são válidas.

---

## Etapa 7 — Segredos no Key Vault + Managed Identity

```powershell
$KV = "$PREFIX-kv"
az keyvault create -n $KV -g $RG -l $LOC

az keyvault secret set --vault-name $KV -n SqlConnString `
  --value "Driver={ODBC Driver 18 for SQL Server};Server=tcp:$SQLSRV.database.windows.net,1433;Database=$SQLDB;Uid=$SQLADM;Pwd=$SQLPWD;Encrypt=yes;"
```

Prefira **Managed Identity** entre os serviços (sem senha):
- Dê à identidade do agente/app o papel de leitura no AI Search e acesso ao Azure SQL
  (usuário contido mapeado à identidade).
- Conceda `Cognitive Services OpenAI User` no Azure OpenAI.
- Conceda acesso de leitura de segredos no Key Vault.

---

## Etapa 8 — (Opcional) Hospedar app próprio em Container Apps

Use esta etapa **apenas** se mantiver o orquestrador LangGraph (Opção do fim da
Etapa 6) ou expuser uma API/bot próprio (ex.: integração com Teams).

```powershell
$ENV = "$PREFIX-aca-env"
$APP = "$PREFIX-agent"
az containerapp env create -n $ENV -g $RG -l $LOC

# Build e push da imagem para o ACR (crie um ACR antes) e então:
az containerapp create -n $APP -g $RG --environment $ENV `
  --image "<acr>.azurecr.io/intelbras-agent:latest" `
  --system-assigned `
  --ingress external --target-port 8000 `
  --env-vars LLM_PROVIDER=azure AZURE_OPENAI_ENDPOINT=https://$AOAI.openai.azure.com/
```

---

## Etapa 9 — Testar de ponta a ponta

Faça perguntas que exercitem cada caminho:

- **RAG (PDFs)**: "Como configurar o mesh no roteador Wi-Force W6 1500?"
  → deve acionar a tool de busca no AI Search e responder citando o documento.
- **SQL (dados)**: "Qual loja mais vendeu em março de 2025?"
  → deve gerar `SELECT TOP ...` e executar no Azure SQL.
- **Both**: "Qual câmera com WDR vendeu mais?"
  → busca a spec no AI Search + consulta vendas no SQL e combina.

Verifique no **Application Insights / Azure Monitor** as chamadas de tool, latência
e erros de SQL.

---

## Ajustes de código necessários (POC → Azure)

Mudanças mínimas, isoladas por arquivo:

- `src/llm.py`: adicionar um provider `azure` usando o SDK `AzureOpenAI`
  (`azure_endpoint`, `api_version`, `azure_deployment`). O restante da interface
  `complete()` continua igual.
- `src/rag_agent.py`: trocar `Chroma` + `OpenAIEmbeddings` por consulta ao índice
  do **Azure AI Search** (`azure-search-documents`). `search()`/`format_context()`
  mantêm a mesma assinatura; muda só a origem dos documentos.
- `src/sql_agent.py`: já está em `pyodbc`/SQL Server. Em produção troque para o
  **ODBC Driver 18** e `Encrypt=yes`; considere autenticação via Managed Identity.
- `src/orchestrator.py`: se migrar para o Agent Service, o roteamento vira
  tool-calling do modelo. Se ficar em Container Apps, mantém-se como está.
- `src/config.py`: adicionar `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`,
  `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX`, `AZURE_SEARCH_KEY` (ou Managed Identity).

> Posso implementar o provider `azure` no `llm.py` e a versão AI Search do
> `rag_agent.py` se você quiser dar o próximo passo no código.

---

## Ordem resumida (checklist)

1. `az group create`
2. Azure OpenAI + deployments (gpt-4o, embeddings)
3. Azure SQL + `python scripts/init_database.py`
4. Storage + upload dos PDFs
5. Azure AI Search + "Import and vectorize data" (índice dos PDFs)
6. Schema do banco nas instruções do agente (de `knowledge/dados/*.md`)
7. AI Foundry: agente com tool de AI Search + function tool de SQL
8. Key Vault + Managed Identity
9. (Opcional) Container Apps se mantiver LangGraph/bot próprio
10. Teste ponta a ponta (rag / sql / both) + observabilidade
