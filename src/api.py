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