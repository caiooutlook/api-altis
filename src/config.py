"""Configuração centralizada da aplicação."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KNOWLEDGE_DIR = PROJECT_ROOT / os.getenv("OKF_KNOWLEDGE_PATH", "./knowledge")
CHROMA_PERSIST_PATH = str(PROJECT_ROOT / os.getenv("CHROMA_PERSIST_PATH", "./data/chroma_db"))

# LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# SQL Server Database
SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server")
SQLSERVER_HOST = os.getenv("SQLSERVER_HOST", "localhost")
SQLSERVER_PORT = os.getenv("SQLSERVER_PORT", "1433")
SQLSERVER_DATABASE = os.getenv("SQLSERVER_DATABASE", "intelbras_db")
SQLSERVER_USER = os.getenv("SQLSERVER_USER", "sa")
SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD", "")
# "yes"/"no" - habilita conexão criptografada; "no" facilita ambientes locais/dev
SQLSERVER_ENCRYPT = os.getenv("SQLSERVER_ENCRYPT", "no")
SQLSERVER_TRUST_CERT = os.getenv("SQLSERVER_TRUST_CERT", "yes")
# Timeout (segundos) para estabelecer a conexão. Evita que o endpoint fique
# "pendurado" por ~30s quando o firewall/rede bloqueia o acesso.
SQLSERVER_LOGIN_TIMEOUT = os.getenv("SQLSERVER_LOGIN_TIMEOUT", "15")


def build_sqlserver_conn_str(database: str | None = None) -> str:
    """Monta a connection string ODBC para o SQL Server.

    Args:
        database: nome do banco a conectar. Se None, usa SQLSERVER_DATABASE.
                  Passe "master" para operações de criação de banco.
    """
    db = database if database is not None else SQLSERVER_DATABASE
    return (
        f"DRIVER={{{SQLSERVER_DRIVER}}};"
        f"SERVER={SQLSERVER_HOST},{SQLSERVER_PORT};"
        f"DATABASE={db};"
        f"UID={SQLSERVER_USER};"
        f"PWD={SQLSERVER_PASSWORD};"
        f"Encrypt={SQLSERVER_ENCRYPT};"
        f"TrustServerCertificate={SQLSERVER_TRUST_CERT};"
        f"Connection Timeout={SQLSERVER_LOGIN_TIMEOUT};"
    )


# Connection string padrão (banco da aplicação)
SQLSERVER_CONN_STR = build_sqlserver_conn_str()
