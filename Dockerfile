# Imagem do endpoint da tool SQL (Estratégia A2) para deploy no Azure Container Apps.
# Dentro do container temos root, então o ODBC Driver 18 é instalado sem problema
# de permissão (diferente da máquina local).
# IMPORTANTE: fixamos o Debian 12 (bookworm). A tag "slim" pura passou a apontar
# para o Debian 13 (trixie), que a Microsoft ainda NAO suporta no repositorio ODBC
# (o apt falha com exit 100). Bookworm e oficialmente suportado.
FROM python:3.11-slim-bookworm

# --- Pacotes base para adicionar o repositório da Microsoft ---
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl gnupg ca-certificates apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# --- Repositório da Microsoft + ODBC Driver 18 ---
# O prod.list da Microsoft referencia a chave em /usr/share/keyrings, entao
# gravamos o keyring exatamente nesse caminho (evita "keyring not found").
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
       -o /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala só as dependências do endpoint (imagem enxuta)
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copia apenas o código necessário
COPY src ./src

# Escuta SEMPRE na porta 8000 (fixa). O Ingress do Container App deve usar
# Target port = 8000. Nao dependemos da env var PORT (o Container Apps pode
# injeta-la com outro valor e quebrar o bind, deixando a revisao presa em
# "Ativando" por falha no health probe).
EXPOSE 8000
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
