"""
Agente SQL - Consulta dados operacionais no banco SQL Server.

Responsável por:
- Traduzir perguntas em linguagem natural para SQL
- Executar queries no banco SQL Server (somente SELECT)
- Formatar resultados para apresentação ao usuário
"""

import pyodbc
from typing import Optional

from src.config import SQLSERVER_CONN_STR


# Schema do banco para contexto do LLM
DB_SCHEMA = """
-- Tabelas disponíveis no banco de dados Intelbras:

CREATE TABLE lojas (
    id INT PRIMARY KEY,
    nome VARCHAR(100),        -- nome da loja (ex: "Intelbras Florianópolis Centro")
    cidade VARCHAR(60),       -- cidade (ex: "Florianópolis")
    estado VARCHAR(2),        -- UF (ex: "SC")
    regiao VARCHAR(20),       -- região geográfica (Sul, Sudeste, Nordeste, Centro-Oeste)
    telefone VARCHAR(20)
);

CREATE TABLE funcionarios (
    id INT PRIMARY KEY,
    nome VARCHAR(100),        -- nome completo
    cargo VARCHAR(60),        -- cargo (Gerente de Loja, Vendedor, Vendedora, Técnico de Suporte)
    loja_id INT,              -- FK → lojas.id
    email VARCHAR(100),
    data_admissao DATE,
    salario DECIMAL(10,2)
);

CREATE TABLE produtos (
    id INT PRIMARY KEY,
    codigo VARCHAR(30) UNIQUE, -- código do produto (ex: "VIP-1230-D")
    nome VARCHAR(120),         -- nome completo do produto
    categoria VARCHAR(40),     -- categoria (Câmeras, Gravadores, Redes, Alarmes, Comunicação, Controle de Acesso)
    preco_unitario DECIMAL(10,2),
    descricao VARCHAR(500)
);

CREATE TABLE estoque (
    id INT PRIMARY KEY,
    produto_id INT,           -- FK → produtos.id
    loja_id INT,              -- FK → lojas.id
    quantidade INT,           -- quantidade em estoque
    ultima_atualizacao DATE
);

CREATE TABLE vendas (
    id INT PRIMARY KEY,
    produto_id INT,           -- FK → produtos.id
    loja_id INT,              -- FK → lojas.id
    funcionario_id INT,       -- FK → funcionarios.id
    quantidade INT,           -- quantidade vendida
    valor_total DECIMAL(10,2), -- valor total da venda
    data_venda DATE           -- data da venda (dados de Jan-Mar 2025)
);
"""

# Exemplos de queries para few-shot prompting
EXAMPLE_QUERIES = """
Exemplos de perguntas e queries SQL correspondentes:

Pergunta: "Quantas câmeras VIP 1230 D foram vendidas no total?"
SQL: SELECT SUM(v.quantidade) as total_vendido FROM vendas v JOIN produtos p ON v.produto_id = p.id WHERE p.codigo = 'VIP-1230-D';

Pergunta: "Qual loja vendeu mais em março de 2025?"
SQL: SELECT TOP 5 l.nome, SUM(v.valor_total) as total FROM vendas v JOIN lojas l ON v.loja_id = l.id WHERE v.data_venda >= '2025-03-01' AND v.data_venda < '2025-04-01' GROUP BY l.nome ORDER BY total DESC;

Pergunta: "Quais produtos têm estoque zero na loja de São Paulo?"
SQL: SELECT p.nome, p.codigo FROM produtos p WHERE p.id NOT IN (SELECT e.produto_id FROM estoque e JOIN lojas l ON e.loja_id = l.id WHERE l.cidade = 'São Paulo' AND e.quantidade > 0);

Pergunta: "Quem são os funcionários da loja de Curitiba?"
SQL: SELECT f.nome, f.cargo, f.email FROM funcionarios f JOIN lojas l ON f.loja_id = l.id WHERE l.cidade = 'Curitiba';

Pergunta: "Qual o faturamento total por categoria de produto?"
SQL: SELECT p.categoria, SUM(v.valor_total) as faturamento FROM vendas v JOIN produtos p ON v.produto_id = p.id GROUP BY p.categoria ORDER BY faturamento DESC;
"""


class SQLAgent:
    """Agente SQL que consulta o banco de dados SQL Server da Intelbras."""

    def __init__(self):
        self._conn: Optional[pyodbc.Connection] = None

    def get_connection(self) -> pyodbc.Connection:
        """Obtém conexão com o banco SQL Server."""
        if self._conn is None:
            self._conn = pyodbc.connect(SQLSERVER_CONN_STR, autocommit=True)
            # Garante que textos (VARCHAR/NVARCHAR) sejam lidos/escritos como UTF-8.
            # Sem isso, no Linux o driver ODBC devolve acentos errados
            # (ex.: "São Paulo" vira "SÃ£o Paulo").
            self._conn.setdecoding(pyodbc.SQL_CHAR, encoding="utf-8")
            self._conn.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-8")
            self._conn.setencoding(encoding="utf-8")
        return self._conn

    def close(self):
        """Fecha a conexão."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def validate_query(self, sql: str) -> tuple[bool, str]:
        """
        Valida se a query é segura para execução.
        Retorna (is_valid, message).
        """
        sql_upper = sql.strip().upper()

        # Apenas SELECT é permitido
        if not sql_upper.startswith("SELECT"):
            return False, "Apenas consultas SELECT são permitidas."

        # Bloqueia operações perigosas
        dangerous_keywords = [
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
            "CREATE", "TRUNCATE", "EXEC", "EXECUTE",
            "GRANT", "REVOKE", "SHUTDOWN",
        ]
        for keyword in dangerous_keywords:
            # Verifica se aparece como palavra isolada (não dentro de um nome de coluna)
            if f" {keyword} " in f" {sql_upper} ":
                return False, f"Operação '{keyword}' não permitida."

        return True, "OK"

    def execute_query(self, sql: str, max_rows: int = 50) -> dict:
        """
        Executa uma query SELECT no banco SQL Server.

        Args:
            sql: Query SQL (somente SELECT)
            max_rows: Limite de linhas retornadas

        Returns:
            dict com: columns, rows, row_count, truncated, error
        """
        # Validação de segurança
        is_valid, message = self.validate_query(sql)
        if not is_valid:
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "truncated": False,
                "error": message,
            }

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql)

            # Obtém nomes das colunas
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Busca resultados com limite
            rows = []
            truncated = False
            for i, row in enumerate(cursor.fetchall()):
                if i >= max_rows:
                    truncated = True
                    break
                # Converte para tipos serializáveis
                rows.append([self._serialize_value(v) for v in row])

            cursor.close()

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": truncated,
                "error": None,
            }

        except Exception as e:
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "truncated": False,
                "error": f"Erro ao executar query: {str(e)}",
            }

    def _serialize_value(self, value) -> str:
        """Converte valores do JDBC para string legível."""
        if value is None:
            return "NULL"
        return str(value)

    def format_results(self, result: dict) -> str:
        """Formata os resultados da query para apresentação ao usuário."""
        if result["error"]:
            return f"❌ Erro: {result['error']}"

        if result["row_count"] == 0:
            return "Nenhum resultado encontrado para esta consulta."

        # Formata como tabela
        columns = result["columns"]
        rows = result["rows"]

        # Calcula largura de cada coluna
        widths = [len(col) for col in columns]
        for row in rows:
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(str(val)))

        # Header
        header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
        separator = "-+-".join("-" * widths[i] for i in range(len(columns)))

        # Rows
        formatted_rows = []
        for row in rows:
            formatted_row = " | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row))
            formatted_rows.append(formatted_row)

        table = f"{header}\n{separator}\n" + "\n".join(formatted_rows)

        if result["truncated"]:
            table += f"\n\n(... resultados truncados, exibindo primeiras {result['row_count']} linhas)"

        return table

    def get_schema(self) -> str:
        """Retorna o schema do banco para uso como contexto."""
        return DB_SCHEMA

    def get_sql_prompt(self, query: str) -> str:
        """Monta o prompt para o LLM gerar a query SQL."""
        return f"""Você é um assistente especializado em gerar consultas SQL para o banco de dados da Intelbras.
O banco usa Microsoft SQL Server (T-SQL).

{DB_SCHEMA}

{EXAMPLE_QUERIES}

REGRAS:
1. Gere APENAS queries SELECT (leitura).
2. Use JOINs quando precisar cruzar tabelas.
3. Use aliases claros para legibilidade.
4. Para limitar resultados use TOP N (ex: SELECT TOP 5 ...), NUNCA use LIMIT.
5. Para datas, use formato 'YYYY-MM-DD'.
6. Os dados de vendas vão de Janeiro a Março de 2025.
7. Retorne APENAS a query SQL, sem explicação, sem markdown, sem ```sql.

PERGUNTA DO USUÁRIO: {query}

SQL:"""

    def get_interpretation_prompt(self, query: str, sql: str, results: str) -> str:
        """Prompt para o LLM interpretar os resultados da query."""
        return f"""Você é um assistente de dados da Intelbras. O usuário fez uma pergunta e os dados foram consultados no banco.
Interprete os resultados de forma clara e objetiva em português.
Se os dados estiverem vazios, informe que não foram encontrados resultados.
Formate valores monetários em R$ com separador de milhar.

PERGUNTA DO USUÁRIO: {query}

QUERY SQL EXECUTADA: {sql}

RESULTADOS:
{results}

INTERPRETAÇÃO:"""
