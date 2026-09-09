# Imagem do endpoint da tool SQL (Estratégia A2) para deploy no Azure Container Apps.
# Dentro do container temos root, então o ODBC Driver 18 é instalado sem problema
# de permissão (diferente da máquina local).
FROM python:3.11-slim

# --- Pacotes base necessários para adicionar o repositório da Microsoft ---
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl gnupg ca-certificates apt-transport-https unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# --- Repositório da Microsoft (detecta a versão do Debian automaticamente) ---
# Fixar a versão errada do Debian faz o apt-get falhar (exit 100). Aqui lemos a
# versão real da imagem base a partir de /etc/os-release.
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /etc/apt/keyrings/microsoft-prod.gpg \
    && . /etc/os-release \
    && curl -fsSL "https://packages.microsoft.com/config/debian/${VERSION_ID}/prod.list" \
       | sed 's#deb https://#deb [signed-by=/etc/apt/keyrings/microsoft-prod.gpg] https://#' \
       > /etc/apt/sources.list.d/mssql-release.list

# --- ODBC Driver 18 for SQL Server ---
RUN apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala só as dependências do endpoint (imagem enxuta)
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copia apenas o código necessário
COPY src ./src

# App Service injeta a porta em $PORT; usamos 8000 como padrão local.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
