# Deploy da Arquitetura na Azure — Passo a Passo (Portal Web)

Guia 100% pela **interface web** (Azure Portal e Azure AI Foundry). Nenhum comando
de CLI. Cada etapa descreve os cliques e campos a preencher.

Arquitetura (igual à do guia por CLI):

- **Agente SQL**: lê o OKF/knowledge que descreve a estrutura do banco
  (`knowledge/dados/*.md`) para montar SQL e consultar o **Azure SQL Database**.
- **Agente RAG**: usa uma **base de conhecimento** no **Azure AI Search** alimentada
  por **PDFs** (datasheets/manuais) guardados no **Blob Storage**.
- **Orquestração**: **Azure AI Foundry Agent Service** — o próprio modelo decide,
  via tools, quando buscar documentação (RAG) e quando consultar dados (SQL).

> Portais usados:
> - **Azure Portal**: https://portal.azure.com
> - **Azure AI Foundry**: https://ai.azure.com

---

## Convenções de nomes (sugestão)

| Recurso | Nome sugerido |
|---------|---------------|
| Resource Group | `rg-intelbras-ia` |
| Região | `East US 2` |
| Azure OpenAI | `intelbras-aoai` |
| AI Search | `intelbras-search` |
| Storage Account | `intelbrasstg` |
| SQL Server | `intelbras-sqlsrv` |
| SQL Database | `intelbras_db` |
| Key Vault | `intelbras-kv` |
| AI Foundry Hub | `intelbras-hub` |
| AI Foundry Project | `intelbras-project` |

---

## Etapa 0 — Criar o Resource Group

1. No Azure Portal, na barra de busca do topo, digite **Resource groups** e abra.
2. Clique **+ Create**.
3. Preencha:
   - **Subscription**: sua assinatura.
   - **Resource group**: `rg-intelbras-ia`.
   - **Region**: `East US 2`.
4. **Review + create** → **Create**.

> Dica: crie todos os recursos abaixo **na mesma região e resource group** para
> reduzir latência e simplificar permissões.

---

## Etapa 1 — Azure OpenAI (LLM + Embeddings)

### 1.1 Criar o recurso

1. Busque **Azure OpenAI** → **+ Create**.
2. Aba **Basics**:
   - **Resource group**: `rg-intelbras-ia`.
   - **Region**: `East US 2`.
   - **Name**: `intelbras-aoai`.
   - **Pricing tier**: `Standard S0`.
3. **Review + create** → **Create**.

> Se o Azure OpenAI não aparecer, a assinatura pode precisar de habilitação prévia
> (formulário de acesso). Verifique com o time responsável pela subscription.

### 1.2 Publicar os deployments no AI Foundry

1. Abra o recurso criado → botão **Go to Azure AI Foundry portal** (ou acesse
   https://ai.azure.com e selecione o recurso).
2. Menu lateral **Deployments** → **+ Deploy model** → **Deploy base model**.
3. Crie **dois** deployments:
   - **Modelo**: `gpt-4o` → nome do deployment: `gpt-4o`.
   - **Modelo**: `text-embedding-3-small` → nome do deployment: `text-embedding-3-small`.
4. Para cada um, defina a capacidade (TPM) conforme a cota disponível e confirme.

Anote (menu **Overview / Keys and Endpoint** do recurso no portal):
- **Endpoint**: `https://intelbras-aoai.openai.azure.com/`
- **Key** (ou use Managed Identity mais adiante).

---

## Etapa 2 — Azure SQL Database (agente SQL)

### 2.1 Criar servidor + banco

1. Busque **SQL databases** → **+ Create**.
2. Aba **Basics**:
   - **Resource group**: `rg-intelbras-ia`.
   - **Database name**: `intelbras_db`.
   - **Server**: clique **Create new**:
     - **Server name**: `intelbras-sqlsrv`.
     - **Location**: `East US 2`.
     - **Authentication method**: `Use SQL authentication`.
     - **Server admin login**: `sqladmin`.
     - **Password**: defina uma senha forte.
     - **OK**.
   - **Compute + storage**: clique **Configure** e escolha, por exemplo,
     `Standard S0` (ou o menor DTU/vCore que atenda a POC).
3. **Review + create** → **Create**.

### 2.2 Liberar acesso (firewall)

1. Abra o **SQL server** `intelbras-sqlsrv` → menu **Networking**.
2. Em **Firewall rules**:
   - Ligue **Allow Azure services and resources to access this server** (para POC).
   - Clique **Add your client IPv4 address** (para você conseguir rodar o script
     de carga a partir da sua máquina).
3. **Save**.

> Em produção, troque isso por **Private Endpoint** e desligue o acesso público.

### 2.3 Popular o banco (tabelas + views + tabela materializada)

O script `scripts/init_database.py` cria tudo (tabelas, views e a tabela
`tb_ia_fonte_dados` usada para indexação de dados de negócio, se necessário).

1. No seu `.env` local, aponte para o Azure SQL:
   ```
   SQLSERVER_HOST=intelbras-sqlsrv.database.windows.net
   SQLSERVER_PORT=1433
   SQLSERVER_DATABASE=intelbras_db
   SQLSERVER_USER=sqladmin
   SQLSERVER_PASSWORD=<senha>
   SQLSERVER_ENCRYPT=yes
   SQLSERVER_TRUST_CERT=no
   ```
2. Rode localmente: `python scripts/init_database.py`.

> Alternativa sem sua máquina: abra o **Query editor (preview)** do banco no portal
> (menu do database) e cole o SQL de criação/carga manualmente. O script Python é
> mais prático porque já contém tudo em ordem.

---

## Etapa 3 — Storage + upload dos PDFs (fonte do RAG)

### 3.1 Criar a Storage Account

1. Busque **Storage accounts** → **+ Create**.
2. Aba **Basics**:
   - **Resource group**: `rg-intelbras-ia`.
   - **Storage account name**: `intelbrasstg` (precisa ser único; ajuste se necessário).
   - **Region**: `East US 2`.
   - **Redundancy**: `LRS` (suficiente para POC).
3. **Review + create** → **Create**.

### 3.2 Criar container e subir PDFs

1. Abra a Storage Account → menu **Containers** → **+ Container**.
   - **Name**: `produtos-pdfs`.
   - **Anonymous access level**: `Private`.
   - **Create**.
2. Abra o container `produtos-pdfs` → **Upload**.
3. Arraste os PDFs (datasheets/manuais) e confirme o upload.

---

## Etapa 4 — Azure AI Search + indexação dos PDFs (agente RAG)

### 4.1 Criar o serviço

1. Busque **AI Search** (Azure AI Search) → **+ Create**.
2. Aba **Basics**:
   - **Resource group**: `rg-intelbras-ia`.
   - **Service name**: `intelbras-search`.
   - **Location**: `East US 2`.
   - **Pricing tier**: clique **Change** e escolha **Standard** (necessário para
     busca vetorial em escala; Basic serve para testes menores).
3. **Review + create** → **Create**.

### 4.2 Importar e vetorizar os PDFs (wizard)

1. Abra o `intelbras-search` → botão **Import and vectorize data** (na aba Overview).
2. **Connect to your data**:
   - **Data source**: `Azure Blob Storage`.
   - Selecione a Storage Account `intelbrasstg` e o container `produtos-pdfs`.
3. **Vectorize your text**:
   - **Kind**: `Azure OpenAI`.
   - Selecione o recurso `intelbras-aoai` e o deployment `text-embedding-3-small`.
4. **Vectorize and enrich** (opcional): pode deixar OCR/extração de imagens conforme
   necessidade dos seus PDFs.
5. **Advanced settings**:
   - **Enable semantic ranker**: recomendado (melhora relevância).
   - **Schedule**: defina para reindexar periodicamente quando adicionar novos PDFs.
6. **Review and create**:
   - **Objects name prefix**: por exemplo `produtos` (gera `produtos-index`,
     `produtos-indexer`, `produtos-skillset`, `produtos-datasource`).
   - **Create**.

O wizard cria automaticamente: **data source**, **skillset** (extrai texto → divide
em chunks → gera embeddings), **index** (com campo vetorial) e **indexer** que roda a
ingestão.

### 4.3 Validar a indexação

1. No AI Search, menu **Indexers** → abra `produtos-indexer` e confirme o status
   **Success** e a contagem de documentos processados.
2. Menu **Indexes** → abra `produtos-index` → **Search explorer** → faça uma busca
   (ex.: "configurar mesh") e verifique se retorna trechos dos PDFs.

Anote:
- **Search endpoint**: `https://intelbras-search.search.windows.net`
- **Index name**: `produtos-index`
- (Se não usar Managed Identity) **Query key**: menu **Keys**.

---

## Etapa 5 — Conhecimento de schema para o agente SQL

O agente SQL precisa do schema do banco para montar as queries. Hoje o
`sql_agent.py` já traz esse schema em `DB_SCHEMA`, e ele reflete
`knowledge/dados/*.md`.

**Opção recomendada (simples):** copie o conteúdo do schema para as **Instructions**
do agente (Etapa 6). Inclua também as regras que já estão no código:
- Somente `SELECT`.
- Usar `TOP N` (não `LIMIT`).
- Datas no formato `YYYY-MM-DD`.
- Dados de vendas de Jan a Mar/2025.

**Opção avançada:** repita a Etapa 4 criando um **segundo índice** (ex.: `schema-index`)
a partir de `knowledge/dados/*.md` e dê ao agente uma tool de busca de schema. Só
compensa se o schema crescer bastante.

---

## Etapa 6 — Criar o agente no Azure AI Foundry

### 6.1 Hub e Project

1. Acesse https://ai.azure.com.
2. Se ainda não existir, crie um **Hub**:
   - **+ New hub** → **Name**: `intelbras-hub`, **Resource group**: `rg-intelbras-ia`,
     **Region**: `East US 2`, e conecte o recurso Azure OpenAI `intelbras-aoai`.
3. Dentro do hub, **+ New project** → **Name**: `intelbras-project`.

### 6.2 Conectar recursos ao project

1. No project, menu **Management center / Connected resources** (ou **Settings**):
   - Confirme a conexão com **Azure OpenAI** (`intelbras-aoai`).
   - Adicione uma **Connection** para o **Azure AI Search** (`intelbras-search`).

### 6.3 Criar o agente e as tools (detalhado)

#### Como o agente "decide" qual fonte usar

Diferente da POC, onde o `orchestrator.py` classifica a intenção com um prompt e
roteia via LangGraph (`classify_intent` → `rag`/`sql`/`both`), no Agent Service quem
decide é o **próprio modelo (gpt-4o) via tool-calling**. O mecanismo é este:

1. Você registra **duas tools** no agente, cada uma com um **nome** e uma
   **descrição** em linguagem natural.
2. A cada pergunta, o modelo lê: as **Instructions** do agente + as **descrições
   das tools** + a pergunta do usuário.
3. O modelo escolhe **qual(is)** tool(s) chamar com base nessas descrições. Ele
   pode chamar uma, a outra, ou **as duas em sequência** (o equivalente ao "both").
4. Se nenhuma tool for necessária (ex.: "bom dia"), ele responde direto (equivale
   ao "general").

Ou seja: **a descrição das tools é o "roteador"**. Quanto mais clara a descrição do
"quando usar", melhor o roteamento. As Instructions reforçam a política.

#### Passo a passo

1. Menu **Agents** → **+ New agent**.
2. **Name**: `assistente-intelbras`.
3. **Model / Deployment**: selecione `gpt-4o`.
4. **Instructions**: cole o texto abaixo (system prompt + schema + política de
   roteamento). Ajuste o schema conforme `sql_agent.py`/`knowledge/dados/*.md`:

   ```
   Você é o assistente virtual da Intelbras. Você tem duas fontes:

   1) Uma base de conhecimento (documentação técnica de produtos: manuais,
      datasheets, configurações, especificações, resolução de problemas).
   2) Uma função de consulta ao banco de dados operacional (vendas, faturamento,
      estoque, disponibilidade, lojas, funcionários, preços, quantidades).

   COMO ESCOLHER A FONTE:
   - Perguntas sobre COMO algo funciona, COMO configurar/instalar, especificações
     técnicas ou resolução de problemas → use a base de conhecimento (documentação).
   - Perguntas sobre NÚMEROS de negócio (quanto vendeu, quanto tem em estoque,
     qual loja, ranking, faturamento, disponibilidade) → use a função consultar_dados.
   - Se a pergunta exigir os dois tipos (ex.: "qual câmera com WDR vendeu mais?"),
     use PRIMEIRO a documentação para identificar o produto e DEPOIS consultar_dados
     para os números, e então combine as duas respostas.
   - Saudações ou conversa geral → responda diretamente, sem usar tools.

   REGRAS PARA consultar_dados:
   - Gere apenas comandos SELECT.
   - Use TOP N (nunca LIMIT).
   - Datas no formato 'YYYY-MM-DD'. Os dados de vendas vão de Jan a Mar de 2025.

   ESQUEMA DO BANCO (use para montar o SQL):
   -- lojas(id, nome, cidade, estado, regiao, telefone)
   -- funcionarios(id, nome, cargo, loja_id→lojas.id, email, data_admissao, salario)
   -- produtos(id, codigo, nome, categoria, preco_unitario, descricao)
   -- estoque(id, produto_id→produtos.id, loja_id→lojas.id, quantidade, ultima_atualizacao)
   -- vendas(id, produto_id→produtos.id, loja_id→lojas.id, funcionario_id→funcionarios.id,
   --        quantidade, valor_total, data_venda)

   Sempre cite o produto/documento quando responder com base na documentação.
   ```

5. **Knowledge** → **+ Add knowledge** → **Azure AI Search (Foundry IQ)**:

   No AI Foundry, a base de conhecimento (Knowledge) do agente é ligada a um
   **Serviço de Pesquisa (Azure AI Search)**, que por sua vez está conectado aos
   **documentos PDF no Blob** (o índice criado na Etapa 4). A ligação é assim:

   ```
   Agente ── Knowledge ──> Azure AI Search (índice) ──> Blob (PDFs)
   ```

   Passos:
   - **Select connection**: escolha a conexão do `intelbras-search` (Etapa 6.2). Se
     ela não existir, clique **+ New connection** → **Azure AI Search** → selecione
     o serviço `intelbras-search` e autentique (Key ou Managed Identity).
   - **Select index**: `produtos-index` (o índice gerado pelo wizard "Import and
     vectorize data", que aponta para o container `produtos-pdfs`).
   - **Query type**: `Vector semantic hybrid` (se ativou o semantic ranker) — senão
     `Vector` ou `Keyword`.
   - **Embedding model / vectorizer**: confirme que usa o deployment
     `text-embedding-3-small` (o mesmo da indexação; precisa bater).
   - **Name / Description** da knowledge source (importante para o roteamento):
     "Documentação técnica de produtos Intelbras: manuais, datasheets,
     especificações, instalação, configuração e resolução de problemas."
   - **Add / Save**.

   > Se o índice não aparecer aqui, é porque a Etapa 4 (Import and vectorize data)
   > não foi concluída — volte e confirme que o `produtos-indexer` rodou com status
   > **Success**. O vínculo com o Blob é feito lá, não nesta tela.

   Esta é a fonte do **agente RAG**. Quando o modelo decidir que a pergunta é
   técnica, ele busca aqui automaticamente (substitui o `rag_agent.search()` da POC).

---

#### 6. O acesso ao banco de dados — leia isto com atenção

Aqui está o ponto que costuma confundir (e o motivo de você **não ver** onde
configurar a conexão com o banco, nem a tool "Function"):

**O AI Foundry não conecta no seu banco de dados.** Não existe, no portal, um campo
"connection string do SQL" para o agente. O agente só sabe **conversar** e **chamar
tools**; quem fala com o Azure SQL é um **código seu**, hospedado por você. O portal
apenas **declara** que a tool existe e qual o formato dela.

Por isso, a forma de dar acesso ao banco depende do tipo de tool. Escolha **uma**:

**Opção A — OpenAPI tool (recomendada, configurável pelo portal do agente).**
Você hospeda um pequeno serviço REST (Etapa 8) com um endpoint, por exemplo
`POST /consultar-dados`, que recebe `{ "pergunta": "..." }`, gera o SQL a partir do
schema (reaproveitando `sql_agent.py`), valida que é `SELECT`, executa no Azure SQL
via `pyodbc` e devolve os resultados em JSON. No agente:
   - **Tools / Actions** → **+ Add** → **OpenAPI 3.0 specified tool**.
   - Cole a **especificação OpenAPI** do seu endpoint (exemplo mais abaixo).
   - Configure a autenticação do endpoint (API key ou Managed Identity).
   - A `description` da operação no OpenAPI ensina o modelo **quando** chamá-la.

   > É aqui que "a conexão com o banco" mora: **dentro do seu endpoint**, não no
   > Foundry. O Foundry só chama a URL; o `pyodbc` roda no seu App Service/Container.

**Opção B — Azure Function tool.**
Igual à Opção A, mas o endpoint é uma **Azure Function** (crie pelo portal na Etapa
8). No agente: **Tools** → **Azure Function** e selecione a function. A conexão com o
SQL fica **dentro do código da Function**.

**Opção C — Function (custom function) do playground.**
Este item **só declara o schema JSON da função**; ele **não executa nada** e **não
tem onde configurar banco**. Serve quando é o **seu próprio app cliente** (não o
playground) que recebe o evento de tool-call, executa o SQL e devolve o resultado
via API. Por isso, no playground puro, essa tool "não aparece pronta para configurar
conexão" — é esperado. Para deploy sem escrever um app cliente, use a **Opção A, B ou D**.

**Opção D — MCP tool (o agente gera o SQL, o MCP server executa) — recomendada.**
Sim, dá para usar **MCP**: o Foundry Agent Service suporta **MCP como tipo de tool**
(hoje GA para o Agent Service; a habilitação do MCP tool pode estar em *preview* em
alguns recursos/regiões). Você registra a **URL de um MCP server de SQL** e o agente
passa a enxergar as tools que esse server expõe. Duas formas de dividir a
responsabilidade:

- **Agente gera o SQL / MCP executa** (o que você perguntou): o MCP server expõe uma
  tool tipo `run_sql(query)` ou `read_query(query)`. O modelo, com o schema nas
  Instructions, **escreve o SELECT** e chama a tool passando o SQL; o MCP server só
  **valida e executa** no Azure SQL, devolvendo as linhas. É o mais próximo do
  `sql_agent.py` (que separa geração e execução).
- **MCP resolve tudo**: o server expõe tools de mais alto nível
  (`list_tables`, `describe_table`, `read_query`) e o agente as combina. Assim o
  agente pode até **descobrir o schema** via MCP em vez de depender das Instructions.

A conexão com o banco vive **dentro do MCP server** (variáveis `SQLSERVER_*`), não no
Foundry. Configuração no portal do agente descrita na **Etapa 6.5** abaixo.

Schema/consulta que a tool representa (vale para A, B ou C):

```json
{
  "name": "consultar_dados",
  "description": "Consulta o banco de dados operacional da Intelbras para responder perguntas sobre vendas, faturamento, estoque, disponibilidade, lojas, funcionários, preços e quantidades. Use quando a pergunta pedir NÚMEROS ou fatos de negócio. NÃO use para dúvidas técnicas de produto (essas vão para a base de conhecimento).",
  "parameters": {
    "type": "object",
    "properties": {
      "pergunta": {
        "type": "string",
        "description": "A pergunta do usuário em linguagem natural sobre dados de negócio."
      }
    },
    "required": ["pergunta"]
  }
}
```

Exemplo mínimo de **OpenAPI** para a Opção A (ajuste a URL do seu endpoint):

```yaml
openapi: 3.0.1
info:
  title: Intelbras SQL Tool
  version: "1.0"
servers:
  - url: https://intelbras-agent-api.azurewebsites.net
paths:
  /consultar-dados:
    post:
      operationId: consultar_dados
      description: >-
        Consulta o banco operacional (vendas, estoque, lojas, funcionários,
        preços, quantidades). Use para perguntas que pedem NÚMEROS de negócio.
        NÃO use para dúvidas técnicas de produto.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                pergunta:
                  type: string
              required: [pergunta]
      responses:
        "200":
          description: Resultado da consulta
          content:
            application/json:
              schema:
                type: object
                properties:
                  colunas: { type: array, items: { type: string } }
                  linhas:  { type: array, items: { type: array, items: { type: string } } }
                  resumo:  { type: string }
```

7. **Save**.

> Fluxo completo de uma pergunta de dados:
> 1. Usuário pergunta "qual loja mais vendeu em março?".
> 2. O modelo (gpt-4o) decide chamar `consultar_dados` e envia `{ "pergunta": "..." }`.
> 3. O Foundry faz `POST` no **seu endpoint** (Opção A/B).
> 4. **Seu código** gera o SQL, valida (só SELECT), roda no **Azure SQL** via `pyodbc`
>    e retorna JSON.
> 5. O modelo recebe o JSON e escreve a resposta final em português.
>
> A "conexão com o banco" existe **só no passo 4**, dentro do seu endpoint — nunca no
> Foundry. Por isso não há (e não deve haver) connection string do SQL no portal do
> agente.

#### Como o roteamento fica na prática

| Pergunta do usuário | O modelo aciona | Por quê |
|---------------------|-----------------|---------|
| "Como configurar o mesh no Wi-Force W6 1500?" | Base de conhecimento (AI Search) | É "como configurar" → documentação |
| "Qual loja mais vendeu em março de 2025?" | `consultar_dados` | Pede número de negócio (ranking de vendas) |
| "Qual câmera com WDR vendeu mais?" | AI Search **e depois** `consultar_dados` | Precisa da spec (WDR) + números de vendas |
| "Bom dia!" | Nenhuma tool | Conversa geral, responde direto |

#### Dicas para o roteamento acertar mais

- **Descrições específicas** vencem descrições genéricas. Liste exemplos de "use
  para..." e "não use para..." em cada tool.
- Repita a **política de escolha** nas Instructions (como no texto acima). Instruções
  e descrições se reforçam.
- Se o agente errar (ex.: tentar responder número de estoque pela documentação),
  ajuste as descrições/instructions e teste de novo no Playground (Etapa 6.4). É um
  ciclo de refinamento, não uma configuração única.
- Mantenha `temperature` baixa para as decisões de tool ficarem mais estáveis.

### 6.4 Testar no Playground

1. No agente, abra o **Playground / Agent playground**.
2. Faça perguntas de cada tipo e verifique quais tools o agente aciona:
   - RAG: "Como configurar o mesh no roteador Wi-Force W6 1500?"
   - SQL: "Qual loja mais vendeu em março de 2025?"
   - Both: "Qual câmera com WDR vendeu mais?"

### 6.5 Alternativa recomendada — SQL via MCP tool

Esta seção substitui as Opções A/B/C do item 6 quando você opta por **MCP**. O ganho:
o agente conversa com o banco através de um **MCP server padronizado**, sem você
manter uma spec OpenAPI custom. E responde diretamente à sua pergunta: **o agente
gera o SQL e o MCP server executa**.

#### O que você precisa

- Um **MCP server de SQL Server** exposto por HTTP (endpoint remoto). Opções:
  - Escrever um pequeno MCP server (Python, com o SDK MCP) que reaproveita
    `sql_agent.py` (`validate_query` + `execute_query`) e expõe as tools
    `read_query(query)`, `list_tables()`, `describe_table(nome)`.
  - Ou usar um MCP server de SQL já pronto e configurá-lo com a connection string do
    Azure SQL.
- Hospedar esse server (App Service/Container Apps — Etapa 8) com **ingress HTTPS**.
  A connection string do banco fica **nas env vars do MCP server** (`SQLSERVER_*`).

#### Desenho das tools do MCP server (para "agente gera, MCP executa")

| Tool MCP | Entrada | O que faz | Segurança |
|----------|---------|-----------|-----------|
| `list_tables` | — | Lista as tabelas (lojas, funcionarios, produtos, estoque, vendas) | leitura |
| `describe_table` | `nome` | Retorna colunas/tipos da tabela | leitura |
| `read_query` | `query` (SELECT) | **Executa o SQL gerado pelo agente** e retorna linhas | valida que é só SELECT (reusa `validate_query`) |

> A validação "somente SELECT" **tem que estar no MCP server** (não confie só no
> prompt). Reaproveite `SQLAgent.validate_query()` para bloquear DROP/DELETE/etc.

#### Configurar o MCP tool no portal do agente

1. No agente (AI Foundry), vá em **Tools / Actions** → **+ Add** → **MCP server**
   (Model Context Protocol).
2. Preencha:
   - **Server URL**: a URL HTTPS do seu MCP server (ex.:
     `https://intelbras-sql-mcp.azurewebsites.net/mcp`).
   - **Server label / name**: `sql-intelbras`.
   - **Headers** (opcional): chaves de autenticação que o server exige (ex.:
     `Authorization: Bearer ...`). O portal permite passar headers custom.
   - **Allowed tools** (se disponível): restrinja a `list_tables`, `describe_table`,
     `read_query` para reduzir superfície.
3. **Approval mode**: por padrão o Foundry pede **aprovação** antes de cada
   chamada de tool MCP. Para POC no Playground, você aprova manualmente; para
   produção, defina a política de aprovação conforme sua necessidade (revise sempre
   dados enviados a servers remotos).
4. **Save**. As tools do MCP server aparecem automaticamente para o agente e são
   atualizadas se o server evoluir.

#### Ajuste nas Instructions (para o agente gerar o SQL certo)

Acrescente às Instructions (Etapa 6.3, item 4):

```
Para dados de negócio, use as tools do MCP server "sql-intelbras":
- Se precisar confirmar estrutura, use list_tables / describe_table.
- Gere um comando SELECT (T-SQL, use TOP em vez de LIMIT, datas 'YYYY-MM-DD')
  e execute-o via read_query. Nunca gere INSERT/UPDATE/DELETE/DDL.
- Interprete as linhas retornadas e responda em português, formatando valores
  monetários em R$.
```

#### Fluxo de uma pergunta de dados via MCP

1. Usuário: "qual loja mais vendeu em março de 2025?".
2. O modelo (opcional) chama `describe_table('vendas')` para conferir colunas.
3. O modelo **gera** `SELECT TOP 1 l.nome, SUM(v.valor_total) ... GROUP BY ... ORDER BY ... DESC`
   e chama `read_query(query=...)`.
4. O **MCP server valida** (só SELECT) e **executa** no Azure SQL, devolvendo as linhas.
5. O modelo interpreta e responde em português.

A conexão com o banco existe **apenas dentro do MCP server** (passo 4). O Foundry só
fala MCP com o server; nunca tem connection string.

> Comparando as abordagens: **OpenAPI (Opção A)** você define o contrato REST e o
> endpoint gera+executa o SQL internamente; **MCP (Opção D)** o próprio agente gera o
> SQL e o server só executa, com descoberta de schema opcional via tools. MCP é mais
> flexível e reaproveitável entre agentes; OpenAPI é mais simples se você já tem um
> endpoint REST.

---

## Etapa 7 — Segredos e permissões (Key Vault + Managed Identity)

### 7.1 Key Vault

1. Busque **Key Vaults** → **+ Create** → **Name**: `intelbras-kv`,
   **Resource group**: `rg-intelbras-ia`, **Region**: `East US 2` → **Create**.
2. Abra o vault → menu **Secrets** → **+ Generate/Import**:
   - **Name**: `SqlConnString`, **Value**: a connection string do Azure SQL.

### 7.2 Managed Identity (sem senhas entre serviços)

Prefira identidade gerenciada em vez de chaves:
1. No serviço que executa o código (App Service/Container Apps), menu **Identity**
   → **System assigned** → **On** → **Save**.
2. Conceda os papéis (via **Access control (IAM)** de cada recurso):
   - No **Azure OpenAI**: role **Cognitive Services OpenAI User**.
   - No **Azure AI Search**: role **Search Index Data Reader**.
   - No **Key Vault**: acesso de leitura de secrets (RBAC ou Access policy).
   - No **Azure SQL**: crie um usuário contido mapeado à identidade.

---

## Etapa 8 — Hospedar o endpoint que acessa o banco (obrigatório para o SQL)

**Esta etapa é onde a conexão com o Azure SQL realmente acontece.** Sem ela, o agente
consegue fazer RAG (documentação), mas **não** consulta dados de negócio, porque o
Foundry não fala com bancos — quem fala é este serviço.

Você hospeda **um** destes (ambos guardam a connection string do banco nas env vars,
nunca no Foundry):

- **um endpoint REST** (Opção A/OpenAPI) — esboço FastAPI abaixo, **ou**
- **um MCP server** (Opção D/MCP — Etapa 6.5), que expõe `read_query`, `list_tables`,
  `describe_table` reaproveitando `sql_agent.py`. Publique-o do mesmo jeito (App
  Service/Container Apps) com **ingress HTTPS** e informe a URL no MCP tool do agente.

Esboço mínimo do endpoint REST (Opção A) que você empacota numa imagem e publica:

```python
# app.py — endpoint que o Foundry chama (Opção A / OpenAPI tool)
from fastapi import FastAPI
from pydantic import BaseModel
from src.sql_agent import SQLAgent
from src.llm import LLMClient   # aponte para Azure OpenAI em produção

app = FastAPI()
sql = SQLAgent()               # usa SQLSERVER_* do ambiente (Azure SQL)
llm = LLMClient()

class Pergunta(BaseModel):
    pergunta: str

@app.post("/consultar-dados")
def consultar_dados(body: Pergunta):
    # 1) LLM gera o SQL a partir do schema (mesmo prompt da POC)
    sql_text = llm.complete(sql.get_sql_prompt(body.pergunta),
                            temperature=0.0, max_tokens=500)
    # 2) valida (somente SELECT) e executa no Azure SQL via pyodbc
    resultado = sql.execute_query(sql_text)
    return {
        "colunas": resultado["columns"],
        "linhas": resultado["rows"],
        "resumo": sql.format_results(resultado),
    }
```

As **variáveis de ambiente** deste serviço são o único lugar com a connection string
do banco: `SQLSERVER_HOST`, `SQLSERVER_DATABASE`, `SQLSERVER_USER`,
`SQLSERVER_PASSWORD` (ou Managed Identity), `SQLSERVER_ENCRYPT=yes`. Também os
endpoints do Azure OpenAI/Search.

### Opção App Service

1. Busque **App Services** → **+ Create**.
2. **Basics**:
   - **Resource group**: `rg-intelbras-ia`.
   - **Name**: `intelbras-agent-api` (bate com a URL do OpenAPI da Etapa 6).
   - **Publish**: `Container` (recomendado) ou `Code` (Python).
   - **Region**: `East US 2`.
3. **Review + create** → **Create**.
4. Menu **Configuration / Environment variables**: adicione as `SQLSERVER_*`, os
   endpoints do Azure OpenAI/Search e (se usar) a referência ao secret do Key Vault.
5. Menu **Identity** → ligue a Managed Identity (Etapa 7.2) para acessar SQL/Search
   sem senha.
6. Copie a URL pública (ex.: `https://intelbras-agent-api.azurewebsites.net`) e use-a
   no campo `servers.url` da spec OpenAPI da Etapa 6 (Opção A).

### Opção Container Apps

Análoga: **Container Apps** → **+ Create**, associe a um **Container Apps
Environment**, configure **Ingress** (external, porta do app) e as mesmas **Env vars**.

> Depois de publicar, teste o endpoint direto (ex.: pelo **Test/Console** do App
> Service ou um cliente REST) antes de voltar ao agente: envie
> `{"pergunta":"qual loja mais vendeu em março de 2025?"}` e confirme que retorna
> linhas. Só então valide pelo Playground (Etapa 6.4).

---

## Etapa 9 — Observabilidade (Application Insights)

1. Busque **Application Insights** → **+ Create** → **Resource group**:
   `rg-intelbras-ia`, **Name**: `intelbras-appi` → **Create**.
2. Conecte ao seu App Service/Container Apps (menu **Application Insights** do
   serviço → **Enable/Turn on**).
3. Use **Logs / Failures / Performance** para acompanhar chamadas de tool, latência
   e erros de SQL.

---

## Checklist final (tudo via portal)

1. Resource group criado.
2. Azure OpenAI criado + deployments `gpt-4o` e `text-embedding-3-small` (AI Foundry).
3. Azure SQL criado, firewall liberado, banco populado (`init_database.py`).
4. Storage + container `produtos-pdfs` com os PDFs.
5. AI Search criado + **Import and vectorize data** → `produtos-index` validado.
6. Schema do banco colado nas Instructions do agente (de `knowledge/dados/*.md`).
7. AI Foundry: Hub + Project + Agent.
8. Knowledge (Foundry IQ) ligada ao AI Search `produtos-index` (→ Blob de PDFs).
9. Endpoint SQL publicado (App Service/Container Apps) — **é aqui que mora a conexão
   com o Azure SQL**. Registrado no agente como **MCP server (recomendado, Etapa 6.5)**
   ou OpenAPI/Azure Function tool.
10. Key Vault + Managed Identity + papéis IAM.
11. Application Insights ligado.
12. Testes no Playground: rag / sql / both.

> Importante: o passo 9 **não é opcional** se você quer consultas ao banco. O agente
> só faz RAG sozinho; para dados de negócio, ele chama o **seu endpoint**, e a
> conexão com o SQL existe **apenas lá**, nunca no portal do Foundry.

> Para os ajustes de código (provider `azure` no `llm.py`, versão AI Search do
> `rag_agent.py`, endpoint da função SQL), consulte a seção "Ajustes de código" do
> guia `docs/deploy-azure-passo-a-passo.md`.
