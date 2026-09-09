# Tool de SQL para o Agente — Estratégia A (Endpoint REST + OpenAPI tool)

Guia focado **apenas** na Estratégia A, na variante **A2**: o **agente do Foundry
gera o SQL** (ele já tem o schema/OKF nas Instructions) e o **endpoint só valida e
executa** no Azure SQL. Sem LLM dentro do endpoint, sem MCP, sem Azure Functions.

Ideia central:

```
Agente (Foundry) ──HTTP POST { "sql": "SELECT ..." }──> endpoint /executar-sql ──pyodbc──> Azure SQL
   (conhece o schema/OKF e                                (valida SELECT e executa,
    GERA o SQL)                                            NÃO gera SQL)
```

Por que A2 (e não deixar o endpoint gerar o SQL):
- **Quem conhece a estrutura do banco é o agente** — o schema/OKF fica nas
  Instructions dele. Não faz sentido duplicar o schema numa LLM interna do endpoint.
- Endpoint **sem LLM** = mais simples, mais barato (zero tokens), mais rápido e sem
  risco de a IA interna desalinhar do schema real.
- A responsabilidade fica clara: **agente = gera SQL**, **endpoint = executa com
  segurança**.

A conexão com o banco vive **só dentro do endpoint**. O Foundry nunca tem a
connection string; ele só chama a URL passando o SQL pronto.

> Pré-requisitos: Azure SQL criado e populado (`init_database.py`) e o agente já
> criado no Foundry com o schema/OKF nas Instructions (veja
> `docs/deploy-azure-portal-web.md`, Etapas 2 e 6).

---

## Passo 1 — Escrever o endpoint (FastAPI)

O endpoint recebe o **SQL já pronto** (gerado pelo agente), valida que é só `SELECT`
e executa no Azure SQL. Reaproveita `SQLAgent` (`validate_query` + `execute_query`)
sem alterá-lo — e **não importa o `LLMClient`**.

Crie `src/api.py`:

```python
"""
Endpoint REST que executa SQL como tool do agente (Estratégia A2).

O agente do Foundry (que conhece o schema/OKF) GERA o SQL e chama:
    POST /executar-sql  com  { "sql": "SELECT ..." }
Aqui apenas validamos (somente SELECT) e executamos no Azure SQL. Sem LLM interna.
"""

import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.sql_agent import SQLAgent

app = FastAPI(title="Intelbras SQL Tool", version="2.0")

sql = SQLAgent()  # usa SQLSERVER_* do ambiente (aponta para o Azure SQL)

# Chave simples para proteger o endpoint (o Foundry envia no header).
API_KEY = os.getenv("TOOL_API_KEY", "")


class SqlIn(BaseModel):
    sql: str


class RespostaOut(BaseModel):
    colunas: list[str]
    linhas: list[list[str]]
    resumo: str
    truncado: bool = False
    erro: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/executar-sql", response_model=RespostaOut)
def executar_sql(body: SqlIn, x_api_key: str = Header(default="")):
    # Autenticação simples por header
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida.")

    # Defesa central: SÓ SELECT. Reusa a validação do SQLAgent.
    # (execute_query já chama validate_query internamente, mas validamos aqui
    #  também para responder 400 explicitamente a SQL não permitido.)
    is_valid, msg = sql.validate_query(body.sql)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    resultado = sql.execute_query(body.sql)

    return RespostaOut(
        colunas=resultado["columns"],
        linhas=resultado["rows"],
        resumo=sql.format_results(resultado),
        truncado=resultado["truncated"],
        erro=resultado["error"],
    )
```

Adicione as dependências do servidor web em `requirements.txt`:

```
# API (Estratégia A - tool do agente)
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
```

> Segurança: a validação "somente SELECT" (`validate_query`) é a linha de defesa
> principal, já que o SQL vem "de fora". Ela bloqueia DROP/DELETE/INSERT/UPDATE/
> ALTER/EXEC etc. Considere também usar um **usuário SQL somente-leitura** na
> connection string (defesa em profundidade — veja o Passo 4).

---

## Passo 2 — Testar localmente (opcional)

> ⚠️ **Redes corporativas costumam bloquear o teste local.** O Azure SQL, por padrão,
> usa a política de conexão **Redirect**: o cliente conecta na 1433 e é redirecionado
> para uma porta na faixa **11000–11999**. Muitas redes corporativas bloqueiam essa
> faixa de saída, o que faz o `pyodbc` **travar** e retornar um erro enganoso do tipo
> "Provedor SSL: uma tentativa de conexão falhou". Nesse caso, **pule o teste local e
> vá direto para o deploy no App Service** (Passo 4) — de dentro da Azure essas portas
> são internas e não sofrem o bloqueio.
>
> Como confirmar o bloqueio: `Test-NetConnection intelbras.database.windows.net -Port 11000`
> falha (timeout) enquanto a porta 1433 conecta. Se você tiver acesso ao portal, pode
> mudar **SQL server → Networking → Connection policy** para **Proxy** (tudo passa pela
> 1433) e o teste local passa a funcionar.

Se a sua rede permitir (ou o servidor estiver em modo Proxy), valide na sua máquina:

1. No `.env`, confirme as variáveis do banco (o endpoint **não** precisa de LLM):
   ```
   SQLSERVER_HOST=intelbras-sqlsrv.database.windows.net
   SQLSERVER_PORT=1433
   SQLSERVER_DATABASE=intelbras_db
   SQLSERVER_USER=app_readonly
   SQLSERVER_PASSWORD=<senha>
   SQLSERVER_ENCRYPT=yes
   SQLSERVER_TRUST_CERT=no

   TOOL_API_KEY=uma-chave-secreta-qualquer
   ```
2. Suba o servidor localmente (rode você mesmo no terminal):
   ```
   uvicorn src.api:app --host 0.0.0.0 --port 8000
   ```
3. Em outro terminal, teste com um SQL pronto (como o agente faria):
   ```
   curl -X POST http://localhost:8000/executar-sql ^
     -H "Content-Type: application/json" ^
     -H "x-api-key: uma-chave-secreta-qualquer" ^
     -d "{\"sql\": \"SELECT TOP 5 l.nome, SUM(v.valor_total) AS total FROM vendas v JOIN lojas l ON v.loja_id = l.id WHERE v.data_venda >= '2025-03-01' AND v.data_venda < '2025-04-01' GROUP BY l.nome ORDER BY total DESC\"}"
   ```
   Deve retornar `colunas`, `linhas` e `resumo`.
4. Teste a segurança: envie um `DELETE` e confirme que retorna **400** (bloqueado).

> Se der erro de conexão, revise o firewall do SQL (libere seu IP) e as `SQLSERVER_*`.
> Se der erro de driver ODBC, instale o **ODBC Driver 18 for SQL Server**.

---

## Passo 3 — Empacotar em container (Dockerfile)

O projeto já inclui os arquivos prontos:
- **`Dockerfile`** — instala o **ODBC Driver 18** dentro do container (lá temos root,
  então não há o problema de permissão da máquina local) e sobe o `uvicorn`.
- **`requirements-api.txt`** — só as dependências do endpoint (`fastapi`, `uvicorn`,
  `pyodbc`, `python-dotenv`), sem LLM/RAG. Imagem enxuta.
- **`.dockerignore`** — evita copiar `.env`, `.venv`, `data/` etc. para a imagem
  (o `.env` com a senha **não** entra no container; segredos vão como env vars do
  App Service).

> Como o container usa o **Driver 18**, a env var no App Service deve ser
> `SQLSERVER_DRIVER=ODBC Driver 18 for SQL Server`.

Para publicar sem CLI, use o **Deployment Center** do App Service com **GitHub
Actions** (build automático a partir do repositório). Basta ter o `Dockerfile` no
repo — o passo a passo está no Passo 4.

Publique a imagem num **Azure Container Registry (ACR)** pela interface web:
1. Portal → **Container registries** → **+ Create** → nome `intelbrasacr`,
   resource group `rg-intelbras-ia` → **Create**.
2. Faça o build/push da imagem. Se preferir não usar CLI, use a opção
   **App Service → Deployment Center** com **GitHub Actions** apontando para o seu
   repositório (build automático a cada push).

---

## Passo 4 — Publicar no App Service (interface web)

1. Portal → **App Services** → **+ Create**.
2. **Basics**:
   - **Resource group**: `rg-intelbras-ia`.
   - **Name**: `intelbras-agent-api` (vira a URL
     `https://intelbras-agent-api.azurewebsites.net`).
   - **Publish**: `Container`.
   - **Operating System**: `Linux`.
   - **Region**: `East US 2`.
3. Aba **Container**: aponte para a imagem no ACR `intelbrasacr` (ou configure o
   Deployment Center com GitHub Actions depois de criar).
4. **Review + create** → **Create**.
5. Após criado, menu **Environment variables / Configuration** → adicione:
   - `SQLSERVER_HOST`, `SQLSERVER_PORT`, `SQLSERVER_DATABASE`, `SQLSERVER_USER`,
     `SQLSERVER_PASSWORD`, `SQLSERVER_ENCRYPT=yes`,
     `SQLSERVER_DRIVER=ODBC Driver 18 for SQL Server`.
   - `TOOL_API_KEY=<uma-chave-secreta>` (a mesma que o agente vai enviar).
   - (Não precisa de variáveis de LLM aqui — o endpoint não gera SQL.)
6. Menu **Networking**: garanta acesso do App Service ao SQL (o firewall do SQL com
   "Allow Azure services" ligado já cobre a POC).
7. Teste em produção:
   `https://intelbras-agent-api.azurewebsites.net/health` deve responder
   `{"status":"ok"}`. Depois teste `POST /executar-sql` (como no Passo 2).

> Defesa em profundidade — usuário somente-leitura: crie no banco um login sem
> permissão de escrita e use-o na connection string do endpoint. Assim, mesmo que
> algo passe pela validação, o banco recusa qualquer escrita. Exemplo (rode no
> Query editor do banco, uma vez):
> ```sql
> CREATE USER app_readonly WITH PASSWORD = '<senha-forte>';
> ALTER ROLE db_datareader ADD MEMBER app_readonly;
> ```
> Depois use `SQLSERVER_USER=app_readonly` nas env vars.

> Dica: guarde a senha do SQL no **Key Vault** e referencie via
> `@Microsoft.KeyVault(...)` nas env vars. Para POC, env vars diretas já servem.

---

## Passo 5 — Descrever o endpoint em OpenAPI

O agente precisa de uma **spec OpenAPI** para saber como chamar o endpoint. Note que
o parâmetro agora é **`sql`** (não `pergunta`), porque quem gera o SQL é o agente.
Crie `docs/openapi-sql-tool.yaml` (ajuste a URL para a do seu App Service):

```yaml
openapi: 3.0.1
info:
  title: Intelbras SQL Tool
  description: Executa uma consulta SELECT no banco operacional da Intelbras.
  version: "2.0"
servers:
  - url: https://intelbras-agent-api.azurewebsites.net
paths:
  /executar-sql:
    post:
      operationId: executar_sql
      description: >-
        Executa uma consulta SQL (SOMENTE SELECT, em T-SQL do SQL Server) no banco
        operacional da Intelbras e retorna as linhas. Use quando a pergunta pedir
        NÚMEROS ou fatos de negócio (vendas, faturamento, estoque, disponibilidade,
        lojas, funcionários, preços, quantidades). Você deve GERAR o SQL a partir do
        schema fornecido nas suas instruções. NÃO use para dúvidas técnicas de
        produto (essas vão para a base de conhecimento/documentação).
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                sql:
                  type: string
                  description: >-
                    Comando SELECT em T-SQL (SQL Server). Use TOP N em vez de LIMIT.
                    Datas no formato 'YYYY-MM-DD'. Apenas leitura.
              required: [sql]
      responses:
        "200":
          description: Resultado da consulta
          content:
            application/json:
              schema:
                type: object
                properties:
                  colunas:  { type: array, items: { type: string } }
                  linhas:   { type: array, items: { type: array, items: { type: string } } }
                  resumo:   { type: string }
                  truncado: { type: boolean }
                  erro:     { type: string, nullable: true }
        "400":
          description: SQL não permitido (apenas SELECT é aceito)
```

O campo `description` da operação ensina o modelo **quando** chamar a tool **e** que
ele mesmo deve gerar o SQL. Capriche: "use para números de negócio", "gere o SELECT
a partir do schema", "não use para dúvidas técnicas".

---

## Passo 6 — Registrar a OpenAPI tool no agente (Foundry)

1. Acesse https://ai.azure.com → seu **Project** → **Agents** → abra o
   `assistente-intelbras`.
2. Em **Tools / Actions** → **+ Add** → **OpenAPI 3.0 specified tool**.
3. **Cole** o conteúdo do `openapi-sql-tool.yaml` (ou faça upload do arquivo).
4. **Authentication**:
   - Escolha **API key** (ou **Custom headers**).
   - **Header name**: `x-api-key`.
   - **Value**: o mesmo valor de `TOOL_API_KEY` configurado no App Service.
   - (Alternativa mais segura: **Managed Identity**, se o endpoint validar token
     do Entra ID em vez de API key.)
5. **Save**. A operação `executar_sql` aparece como tool disponível para o agente.

---

## Passo 7 — Instructions do agente (aqui mora o schema/OKF)

**Este passo é o coração da A2.** Como o agente gera o SQL, o schema/OKF precisa
estar nas Instructions dele. Cole o schema (a partir de `knowledge/dados/*.md` /
`DB_SCHEMA` do `sql_agent.py`) e as regras:

```
Você é o assistente da Intelbras. Para dados de negócio (vendas, faturamento,
estoque, disponibilidade, lojas, funcionários, preços, quantidades):

1. GERE um comando SELECT em T-SQL (SQL Server) a partir do ESQUEMA abaixo.
2. Chame a tool executar_sql passando { "sql": "<o SELECT que você gerou>" }.
3. Interprete as "linhas"/"resumo" retornados e responda em português,
   formatando valores monetários em R$ com separador de milhar.

REGRAS DE SQL:
- Apenas SELECT (leitura). Nunca INSERT/UPDATE/DELETE/DDL.
- Use TOP N (nunca LIMIT).
- Datas no formato 'YYYY-MM-DD'. Vendas cobrem Jan a Mar de 2025.
- Use JOINs e aliases claros.

ESQUEMA DO BANCO:
-- lojas(id, nome, cidade, estado, regiao, telefone)
-- funcionarios(id, nome, cargo, loja_id→lojas.id, email, data_admissao, salario)
-- produtos(id, codigo, nome, categoria, preco_unitario, descricao)
-- estoque(id, produto_id→produtos.id, loja_id→lojas.id, quantidade, ultima_atualizacao)
-- vendas(id, produto_id→produtos.id, loja_id→lojas.id, funcionario_id→funcionarios.id,
--        quantidade, valor_total, data_venda)

NÃO use executar_sql para dúvidas técnicas de produto — para essas, use a base de
conhecimento (documentação).
```

> Manter o schema aqui alinhado ao OKF (`knowledge/dados/*.md`): sempre que o banco
> mudar, atualize o OKF e estas Instructions. Como o endpoint não conhece o schema,
> não há um segundo lugar para manter sincronizado.

---

## Passo 8 — Testar no Playground

1. No agente, abra o **Agent playground**.
2. Pergunta de dados: "Qual loja mais vendeu em março de 2025?".
   - No painel de execução, confira que o agente **gerou** um SELECT e chamou
     `executar_sql` com esse SQL; depois veja a resposta interpretada.
3. Pergunta técnica: "Como configurar o mesh no Wi-Force W6 1500?".
   - Confirme que ele **não** chamou `executar_sql` (foi para a base de conhecimento).
4. Teste de segurança: peça algo que induza escrita ("apague as vendas de janeiro").
   - O agente não deve gerar DELETE; se gerar, o endpoint responde 400 e o agente
     deve informar que só faz consultas.

Se o agente gerar SQL ruim, ajuste o ESQUEMA/regras nas Instructions e teste de novo.

---

## Fluxo completo (recapitulando)

1. Usuário pergunta algo de negócio no agente.
2. O modelo (que tem o schema/OKF nas Instructions) **gera o SELECT**.
3. O modelo chama `executar_sql` com `{ "sql": "SELECT ..." }`.
4. O Foundry faz `POST` no seu App Service (header `x-api-key`).
5. O endpoint **valida (só SELECT)** e **executa** no Azure SQL via `pyodbc`.
6. O endpoint devolve JSON (`colunas`, `linhas`, `resumo`).
7. O modelo interpreta e responde ao usuário em português.

Quem conhece a estrutura do banco é o **agente** (passo 2). O endpoint é "burro" de
propósito: só executa com segurança. A connection string existe **apenas** no App
Service.

---

## Checklist (Estratégia A2)

1. `src/api.py` criado — recebe `sql`, valida SELECT, executa (sem LLM interna).
2. `fastapi` + `uvicorn` no `requirements.txt`.
3. Testado localmente (`/health`, `/executar-sql` com SELECT e teste de 400 no DELETE).
4. `Dockerfile` com ODBC Driver 18 + imagem publicada (ACR ou GitHub Actions).
5. App Service `intelbras-agent-api` com env vars (`SQLSERVER_*`, `TOOL_API_KEY`);
   idealmente usuário SQL somente-leitura.
6. `docs/openapi-sql-tool.yaml` com parâmetro `sql` e a URL do App Service.
7. OpenAPI tool `executar_sql` registrada no agente com autenticação por `x-api-key`.
8. Schema/OKF + regras de SQL colados nas Instructions do agente.
9. Testado no Playground (pergunta de dados gera SQL e aciona a tool; técnica não;
   escrita é bloqueada).
