# Deploy do endpoint SQL via Azure Container Apps (conta pessoal Free)

Guia para publicar o endpoint da tool SQL (`src/api.py`, Estratégia A2) no
**Azure Container Apps**, 100% pela interface web. Escolhemos Container Apps porque:

- Roda o seu **Dockerfile** sem alteração (FastAPI + uvicorn).
- É **serverless** e tem **tier de consumo gratuito** — não depende da cota de VM do
  App Service (que estava zerada na sua assinatura).
- Dá uma **URL HTTPS pública** que serve direto como OpenAPI tool do agente.
- Consegue **buildar a imagem a partir do seu GitHub** (via GitHub Actions), sem você
  criar um Container Registry manualmente nem instalar CLI.

Pré-requisitos:
- Código já no GitHub: `https://github.com/caiooutlook/api-altis` (feito).
- Azure SQL `intel` acessível, com **"Allow Azure services and resources"** ligado no
  firewall do SQL server (é o que deixa o Container App conectar).

---

## Passo 1 — Registrar os provedores de recursos

No portal → sua **Subscription** → **Resource providers**, garanta que estão
**Registered** (buscar cada um e clicar **Register** se preciso):

- `Microsoft.App` — Container Apps
- `Microsoft.OperationalInsights` — Log Analytics (o ambiente usa)
- `Microsoft.ContainerRegistry` — se optar por registry próprio (o build via GitHub
  cria um automaticamente, mas registre por garantia)

> Se algum botão **Register** estiver desabilitado, você não tem permissão — mas em
> conta pessoal Free normalmente tem.

---

## Passo 2 — Criar o Container App

1. No portal, busque **Container Apps** → **+ Create** → **Container App**.
2. Aba **Basics**:
   - **Subscription**: a sua.
   - **Resource group**: `rg-intelbras-ia` (ou **Create new**).
   - **Container app name**: `intelbras-sql-tool`.
   - **Region**: escolha uma que suporte Container Apps (ex.: `East US`, `East US 2`,
     `West Europe`). Se der erro de disponibilidade, troque a região.
   - **Container Apps Environment**: clique **Create new** → nome
     `intelbras-aca-env` → deixe o padrão (cria um Log Analytics junto) → **Create**.
3. **NÃO** clique em criar ainda — vá para a aba **Container** (Passo 3).

---

## Passo 3 — Origem da imagem (build a partir do GitHub)

Na aba **Container** você tem duas rotas. A mais simples sem CLI é a **A**.

### Rota A — Build automático do GitHub (recomendada)

Alguns portais oferecem, na criação, a opção de **Deploy from a GitHub repository**
(ou você configura isso depois, em **Deployment** → **Continuous deployment**).

1. Se a tela de criação tiver **"Use quickstart image"** marcada, deixe assim só para
   criar o app; vamos trocar pela imagem real no Passo 5 via Continuous deployment.
2. Ou, se aparecer a opção **GitHub** direto na criação:
   - **Repository**: `caiooutlook/api-altis`
   - **Branch**: `main`
   - **Dockerfile**: `Dockerfile` (na raiz)
   - O Azure cria um **GitHub Actions** que builda a imagem e publica num ACR gerado
     automaticamente.

### Rota B — Imagem quickstart agora, GitHub depois

Se a criação não pedir o GitHub, marque **"Use quickstart image"**
(`Simple hello world container`) só para o app nascer, e configure o build do GitHub
no Passo 5.

Ainda na aba **Container**, defina:
- **Name**: `intelbras-sql-tool`
- (a imagem real virá do build; por ora pode ser a quickstart)

---

## Passo 4 — Ingress (deixar acessível pela internet)

Aba **Ingress**:
- **Ingress**: **Enabled**.
- **Ingress traffic**: **Accepting traffic from anywhere** (para o Foundry chamar).
- **Ingress type**: HTTP.
- **Target port**: **8000** (a porta que o `uvicorn` expõe no Dockerfile).

Depois **Review + create** → **Create**. Aguarde o provisionamento.

> Guarde a **Application URL** que aparece no Overview do app (algo como
> `https://intelbras-sql-tool.<hash>.<region>.azurecontainerapps.io`). É a base da
> sua OpenAPI tool.

---

## Passo 5 — Configurar o build contínuo do GitHub (se usou quickstart)

Se no Passo 3 você usou a imagem quickstart, agora aponte para o seu código:

1. Abra o Container App → menu **Continuous deployment** (ou **Deployment**).
2. **Repository source**: GitHub → autorize o GitHub → selecione:
   - **Organization/Owner**: `caiooutlook`
   - **Repository**: `api-altis`
   - **Branch**: `main`
   - **Dockerfile location**: `./Dockerfile`
3. **Registry**: deixe o Azure **criar um ACR automaticamente** (ou selecione um
   existente).
4. **Start continuous deployment**. Isso cria um workflow do GitHub Actions no seu
   repo, builda a imagem e faz o deploy no Container App a cada push na `main`.
5. Acompanhe o build na aba **Actions** do repositório no GitHub. Quando terminar, o
   Container App passa a rodar a imagem do seu `Dockerfile`.

---

## Passo 6 — Variáveis de ambiente (a conexão com o banco)

O endpoint lê as `SQLSERVER_*` do ambiente. No Container App:

1. Menu **Containers** → aba **Environment variables** → **Edit and deploy**
   (ou edite na criação, na aba Container → Environment variables).
2. Adicione:
   - `SQLSERVER_DRIVER` = `ODBC Driver 18 for SQL Server`
   - `SQLSERVER_HOST` = `intelbras.database.windows.net`
   - `SQLSERVER_PORT` = `1433`
   - `SQLSERVER_DATABASE` = `intel`
   - `SQLSERVER_USER` = `app_readonly`
   - `SQLSERVER_PASSWORD` = `<senha>`  ← idealmente como **Secret** (veja abaixo)
   - `SQLSERVER_ENCRYPT` = `yes`
   - `SQLSERVER_TRUST_CERT` = `no`
   - `TOOL_API_KEY` = `<uma-chave-secreta>`
3. **Deploy**.

> Segredo com Secrets do Container App: em vez de digitar a senha em texto puro, vá
> em **Secrets** → crie `sqlserver-password` e `tool-api-key`, e na env var escolha
> **Reference a secret**. Mais seguro que texto puro.

> De dentro da Azure, o problema das portas 11000–11999 (que travava seu teste local)
> **não existe** — o Container App tem saída de rede normal para o Azure SQL. Por isso
> o deploy aqui funciona onde o local não funcionava.

---

## Passo 7 — Testar o endpoint publicado

Com a **Application URL** do Passo 4:

1. Health check no navegador:
   `https://intelbras-sql-tool.<hash>.<region>.azurecontainerapps.io/health`
   → deve responder `{"status":"ok"}`.
2. Teste o `/executar-sql` (PowerShell, na sua máquina):
   ```powershell
   $base = "https://intelbras-sql-tool.<hash>.<region>.azurecontainerapps.io"
   $body = @{ sql = "SELECT TOP 5 l.nome, SUM(v.valor_total) AS total FROM vendas v JOIN lojas l ON v.loja_id = l.id WHERE v.data_venda >= '2025-03-01' AND v.data_venda < '2025-04-01' GROUP BY l.nome ORDER BY total DESC" } | ConvertTo-Json
   Invoke-RestMethod -Uri "$base/executar-sql" -Method Post -ContentType "application/json" -Headers @{ "x-api-key" = "<sua-chave>" } -Body $body
   ```
   Deve retornar `colunas`, `linhas` e `resumo`.
3. Se o `/health` responde mas o `/executar-sql` dá erro de conexão, revise: firewall
   do SQL com **"Allow Azure services"** ligado e as env vars `SQLSERVER_*`.

---

## Passo 8 — Registrar no agente (OpenAPI tool)

Use a **Application URL** do Container App no `servers.url` da spec OpenAPI
(`docs/openapi-sql-tool.yaml`) e siga o Passo 6 do guia
`deploy-azure-tool-sql-estrategia-a.md`:

- Foundry → agente → **Tools** → **OpenAPI 3.0 specified tool** → cole a spec.
- **Authentication**: header `x-api-key` = valor de `TOOL_API_KEY`.

---

## Notas de custo (conta Free)

- Container Apps tem um **consumo gratuito mensal** (requests + vCPU-s + memória) que
  cobre folgado uma POC. Fora isso, cobra por uso.
- Configure **Scale → Min replicas = 0** para o app "dormir" quando ocioso e não
  consumir recursos (há um pequeno cold start na primeira chamada). Para demo, deixe
  **Min replicas = 1** para respostas imediatas.
- Ao terminar a POC, **delete o resource group** para zerar qualquer custo.

---

## Checklist

1. Provedores `Microsoft.App` e `Microsoft.OperationalInsights` registrados.
2. Container App `intelbras-sql-tool` criado com Environment `intelbras-aca-env`.
3. Ingress habilitado, target port **8000**, tráfego externo.
4. Build a partir do GitHub `caiooutlook/api-altis` (Continuous deployment) OK.
5. Env vars `SQLSERVER_*` + `TOOL_API_KEY` configuradas (senha como Secret).
6. `/health` responde; `/executar-sql` retorna linhas.
7. OpenAPI tool registrada no agente com a URL do Container App.
