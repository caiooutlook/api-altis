# Imagem do endpoint da tool SQL (Estratégia A2) para deploy no Azure App Service.
# Dentro do container temos root, então o ODBC Driver 18 é instalado sem problema
# de permissão (diferente da máquina local).
FROM python:3.11-slim

# --- ODBC Driver 18 for SQL Server ---
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg apt-transport-https ca-certificates unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
       | sed 's#deb #deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] #' \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
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
