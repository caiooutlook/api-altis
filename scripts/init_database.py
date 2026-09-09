"""
Script para inicializar e popular o banco de dados SQL Server com dados de exemplo.

Cria o banco (se não existir) e as tabelas: lojas, funcionarios, produtos,
estoque, vendas e insere dados fictícios representativos da Intelbras.

Uso:
    python scripts/init_database.py
"""

import sys
from pathlib import Path

# Adiciona o projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pyodbc
from src.config import (
    build_sqlserver_conn_str,
    SQLSERVER_CONN_STR,
    SQLSERVER_DATABASE,
    SQLSERVER_HOST,
    SQLSERVER_PORT,
)


def ensure_database():
    """Cria o banco de dados caso ele ainda não exista.

    Conecta ao banco 'master' e executa o CREATE DATABASE em autocommit,
    pois CREATE DATABASE não pode rodar dentro de uma transação.
    """
    master_conn = pyodbc.connect(build_sqlserver_conn_str("master"), autocommit=True)
    try:
        cursor = master_conn.cursor()
        cursor.execute(
            "IF DB_ID(?) IS NULL EXEC('CREATE DATABASE [' + ? + ']')",
            SQLSERVER_DATABASE,
            SQLSERVER_DATABASE,
        )
        cursor.close()
    finally:
        master_conn.close()


def get_connection():
    """Conecta ao banco de dados da aplicação no SQL Server."""
    return pyodbc.connect(SQLSERVER_CONN_STR, autocommit=False)


# Login/usuário adicional criado pelo script.
# Observação: no SQL Server o admin padrão é "sa"; "root" não existe por padrão.
ROOT_LOGIN = "root"
ROOT_PASSWORD = "Intelbras@123"


def create_root_login():
    """Cria o login 'root' no servidor e o mapeia como usuário do banco da aplicação.

    - O LOGIN é criado no escopo do servidor (conexão em 'master').
    - O USER é criado dentro do banco da aplicação e recebe db_owner.

    Concede db_owner apenas no banco da aplicação (não sysadmin no servidor
    inteiro). Caso precise de privilégios de administrador do servidor, veja a
    observação no final desta função.
    """
    # 1) Cria o LOGIN no servidor (master, autocommit)
    master_conn = pyodbc.connect(build_sqlserver_conn_str("master"), autocommit=True)
    try:
        cursor = master_conn.cursor()
        # QUOTENAME evita injeção no nome do login; a senha vai via literal com
        # aspas duplicadas para escapar corretamente.
        safe_password = ROOT_PASSWORD.replace("'", "''")
        cursor.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = ?)
            EXEC('CREATE LOGIN ' + QUOTENAME(?) +
                 ' WITH PASSWORD = ''""" + safe_password + """'', '
                 + 'CHECK_POLICY = OFF, DEFAULT_DATABASE = ' + QUOTENAME(?))
            """,
            ROOT_LOGIN,
            ROOT_LOGIN,
            SQLSERVER_DATABASE,
        )
        cursor.close()
    finally:
        master_conn.close()

    # 2) Cria o USER no banco da aplicação e concede db_owner
    app_conn = pyodbc.connect(SQLSERVER_CONN_STR, autocommit=True)
    try:
        cursor = app_conn.cursor()
        cursor.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = ?)
            EXEC('CREATE USER ' + QUOTENAME(?) + ' FOR LOGIN ' + QUOTENAME(?))
            """,
            ROOT_LOGIN,
            ROOT_LOGIN,
            ROOT_LOGIN,
        )
        cursor.execute(
            "EXEC('ALTER ROLE db_owner ADD MEMBER ' + QUOTENAME(?))",
            ROOT_LOGIN,
        )
        cursor.close()
    finally:
        app_conn.close()

    # Para conceder privilégios de administrador do servidor inteiro (cuidado!),
    # descomente o bloco abaixo:
    # master_conn = pyodbc.connect(build_sqlserver_conn_str("master"), autocommit=True)
    # try:
    #     cur = master_conn.cursor()
    #     cur.execute("EXEC('ALTER SERVER ROLE sysadmin ADD MEMBER ' + QUOTENAME(?))", ROOT_LOGIN)
    #     cur.close()
    # finally:
    #     master_conn.close()


DDL_STATEMENTS = """
-- =============================================================
-- DROP (na ordem inversa das dependências)
-- =============================================================
IF OBJECT_ID('dbo.vendas', 'U') IS NOT NULL DROP TABLE dbo.vendas;
IF OBJECT_ID('dbo.estoque', 'U') IS NOT NULL DROP TABLE dbo.estoque;
IF OBJECT_ID('dbo.funcionarios', 'U') IS NOT NULL DROP TABLE dbo.funcionarios;
IF OBJECT_ID('dbo.produtos', 'U') IS NOT NULL DROP TABLE dbo.produtos;
IF OBJECT_ID('dbo.lojas', 'U') IS NOT NULL DROP TABLE dbo.lojas;

-- =============================================================
-- LOJAS
-- =============================================================
CREATE TABLE lojas (
    id INT PRIMARY KEY,
    nome NVARCHAR(100) NOT NULL,
    cidade NVARCHAR(60) NOT NULL,
    estado NVARCHAR(2) NOT NULL,
    regiao NVARCHAR(20) NOT NULL,
    telefone NVARCHAR(20)
);

-- =============================================================
-- FUNCIONARIOS
-- =============================================================
CREATE TABLE funcionarios (
    id INT PRIMARY KEY,
    nome NVARCHAR(100) NOT NULL,
    cargo NVARCHAR(60) NOT NULL,
    loja_id INT NOT NULL,
    email NVARCHAR(100),
    data_admissao DATE,
    salario DECIMAL(10,2),
    CONSTRAINT fk_func_loja FOREIGN KEY (loja_id) REFERENCES lojas(id)
);

-- =============================================================
-- PRODUTOS
-- =============================================================
CREATE TABLE produtos (
    id INT PRIMARY KEY,
    codigo NVARCHAR(30) NOT NULL UNIQUE,
    nome NVARCHAR(120) NOT NULL,
    categoria NVARCHAR(40) NOT NULL,
    preco_unitario DECIMAL(10,2) NOT NULL,
    descricao NVARCHAR(500)
);

-- =============================================================
-- ESTOQUE (por loja)
-- =============================================================
CREATE TABLE estoque (
    id INT IDENTITY(1,1) PRIMARY KEY,
    produto_id INT NOT NULL,
    loja_id INT NOT NULL,
    quantidade INT NOT NULL DEFAULT 0,
    ultima_atualizacao DATE,
    CONSTRAINT fk_estoque_produto FOREIGN KEY (produto_id) REFERENCES produtos(id),
    CONSTRAINT fk_estoque_loja FOREIGN KEY (loja_id) REFERENCES lojas(id)
);

-- =============================================================
-- VENDAS
-- =============================================================
CREATE TABLE vendas (
    id INT IDENTITY(1,1) PRIMARY KEY,
    produto_id INT NOT NULL,
    loja_id INT NOT NULL,
    funcionario_id INT NOT NULL,
    quantidade INT NOT NULL,
    valor_total DECIMAL(10,2) NOT NULL,
    data_venda DATE NOT NULL,
    CONSTRAINT fk_vendas_produto FOREIGN KEY (produto_id) REFERENCES produtos(id),
    CONSTRAINT fk_vendas_loja FOREIGN KEY (loja_id) REFERENCES lojas(id),
    CONSTRAINT fk_vendas_func FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
);
"""

INSERT_LOJAS = """
INSERT INTO lojas (id, nome, cidade, estado, regiao, telefone) VALUES
(1, 'Intelbras Florianópolis Centro', 'Florianópolis', 'SC', 'Sul', '(48) 3281-9500'),
(2, 'Intelbras São José', 'São José', 'SC', 'Sul', '(48) 3281-9501'),
(3, 'Intelbras Curitiba', 'Curitiba', 'PR', 'Sul', '(41) 3333-4500'),
(4, 'Intelbras São Paulo Paulista', 'São Paulo', 'SP', 'Sudeste', '(11) 4003-7600'),
(5, 'Intelbras Campinas', 'Campinas', 'SP', 'Sudeste', '(19) 3252-1800'),
(6, 'Intelbras Belo Horizonte', 'Belo Horizonte', 'MG', 'Sudeste', '(31) 3223-5000'),
(7, 'Intelbras Recife', 'Recife', 'PE', 'Nordeste', '(81) 3465-2000'),
(8, 'Intelbras Brasília', 'Brasília', 'DF', 'Centro-Oeste', '(61) 3364-9000');
"""

INSERT_FUNCIONARIOS = """
INSERT INTO funcionarios (id, nome, cargo, loja_id, email, data_admissao, salario) VALUES
(1, 'Carlos Eduardo Silva', 'Gerente de Loja', 1, 'carlos.silva@intelbras.com.br', '2019-03-15', 8500.00),
(2, 'Ana Paula Oliveira', 'Vendedora', 1, 'ana.oliveira@intelbras.com.br', '2021-06-01', 4200.00),
(3, 'Ricardo Santos', 'Técnico de Suporte', 1, 'ricardo.santos@intelbras.com.br', '2020-11-10', 5100.00),
(4, 'Fernanda Costa', 'Gerente de Loja', 2, 'fernanda.costa@intelbras.com.br', '2018-01-20', 8800.00),
(5, 'João Pedro Almeida', 'Vendedor', 2, 'joao.almeida@intelbras.com.br', '2022-03-15', 4000.00),
(6, 'Mariana Ferreira', 'Vendedora', 3, 'mariana.ferreira@intelbras.com.br', '2021-08-01', 4300.00),
(7, 'Lucas Mendes', 'Gerente de Loja', 3, 'lucas.mendes@intelbras.com.br', '2017-05-10', 9200.00),
(8, 'Patrícia Rocha', 'Técnica de Suporte', 4, 'patricia.rocha@intelbras.com.br', '2020-02-28', 5500.00),
(9, 'Gustavo Lima', 'Vendedor', 4, 'gustavo.lima@intelbras.com.br', '2023-01-10', 4100.00),
(10, 'Camila Barbosa', 'Gerente de Loja', 4, 'camila.barbosa@intelbras.com.br', '2016-09-01', 9500.00),
(11, 'Roberto Nascimento', 'Vendedor', 5, 'roberto.nascimento@intelbras.com.br', '2022-07-20', 4000.00),
(12, 'Juliana Moreira', 'Vendedora', 6, 'juliana.moreira@intelbras.com.br', '2021-04-15', 4200.00),
(13, 'Thiago Pereira', 'Gerente de Loja', 7, 'thiago.pereira@intelbras.com.br', '2019-11-01', 8700.00),
(14, 'Beatriz Cardoso', 'Vendedora', 7, 'beatriz.cardoso@intelbras.com.br', '2023-05-01', 3900.00),
(15, 'André Souza', 'Técnico de Suporte', 8, 'andre.souza@intelbras.com.br', '2020-08-15', 5300.00);
"""

INSERT_PRODUTOS = """
INSERT INTO produtos (id, codigo, nome, categoria, preco_unitario, descricao) VALUES
(1, 'VIP-1230-D', 'Câmera IP Dome VIP 1230 D', 'Câmeras', 489.90, 'Câmera IP dome 2MP com IR inteligente 30m, lente 2.8mm'),
(2, 'VIP-3230-B', 'Câmera IP Bullet VIP 3230 B', 'Câmeras', 729.90, 'Câmera IP bullet 2MP Full HD com IR 30m e WDR'),
(3, 'VIP-7230-EF', 'Câmera IP Speed Dome VIP 7230 EF', 'Câmeras', 4899.90, 'Câmera speed dome 2MP com zoom óptico 30x'),
(4, 'MHDX-1004-C', 'DVR Multi HD MHDX 1004-C', 'Gravadores', 599.90, 'DVR 4 canais Multi HD 1080p Lite com detecção inteligente'),
(5, 'MHDX-3008-C', 'DVR Multi HD MHDX 3008-C', 'Gravadores', 1299.90, 'DVR 8 canais Multi HD 1080p com inteligência artificial'),
(6, 'NVD-1232', 'NVR NVD 1232', 'Gravadores', 1899.90, 'NVR 32 canais IP até 8MP com inteligência de vídeo'),
(7, 'WI-FORCE-W6-1500', 'Roteador Wi-Force W6 1500', 'Redes', 349.90, 'Roteador Wi-Fi 6 AX1500 dual band com mesh'),
(8, 'AP-1350-AC', 'Access Point AP 1350 AC', 'Redes', 599.90, 'Access point corporativo dual band AC1350 com gerenciamento centralizado'),
(9, 'SF-800-Q+', 'Switch SF 800 Q+ 8 portas', 'Redes', 119.90, 'Switch 8 portas Fast Ethernet 10/100 Mbps'),
(10, 'AMT-8000', 'Central de Alarme AMT 8000', 'Alarmes', 1899.90, 'Central de alarme monitorada com 64 zonas, Ethernet e Wi-Fi'),
(11, 'AMT-4010-SMART', 'Central de Alarme AMT 4010 Smart', 'Alarmes', 699.90, 'Central de alarme com 4 zonas, aplicativo mobile e Wi-Fi'),
(12, 'XPE-3200-IP-PROXY', 'Porteiro Eletrônico XPE 3200 IP', 'Comunicação', 2499.90, 'Porteiro IP com câmera, leitor de cartão e reconhecimento facial'),
(13, 'TIP-125I', 'Telefone IP TIP 125i', 'Comunicação', 399.90, 'Telefone IP empresarial com 2 contas SIP e PoE'),
(14, 'ELC-5001-RF', 'Fechadura Digital ELC 5001 RF', 'Controle de Acesso', 999.90, 'Fechadura digital com biometria, senha, cartão e app'),
(15, 'SS-3530-MF-W', 'Sensor de Abertura SS 3530 MF W', 'Alarmes', 89.90, 'Sensor de abertura sem fio 433MHz para portas e janelas');
"""

INSERT_ESTOQUE = """
INSERT INTO estoque (produto_id, loja_id, quantidade, ultima_atualizacao) VALUES
(1, 1, 45, '2025-01-10'), (1, 2, 30, '2025-01-10'), (1, 3, 22, '2025-01-08'),
(1, 4, 60, '2025-01-12'), (1, 5, 18, '2025-01-09'), (1, 6, 25, '2025-01-11'),
(1, 7, 15, '2025-01-07'), (1, 8, 20, '2025-01-10'),
(2, 1, 20, '2025-01-10'), (2, 2, 15, '2025-01-10'), (2, 3, 12, '2025-01-08'),
(2, 4, 35, '2025-01-12'), (2, 5, 8, '2025-01-09'), (2, 7, 10, '2025-01-07'),
(3, 1, 5, '2025-01-10'), (3, 4, 8, '2025-01-12'), (3, 6, 3, '2025-01-11'),
(4, 1, 35, '2025-01-10'), (4, 2, 28, '2025-01-10'), (4, 3, 20, '2025-01-08'),
(4, 4, 50, '2025-01-12'), (4, 5, 15, '2025-01-09'), (4, 6, 18, '2025-01-11'),
(4, 7, 12, '2025-01-07'), (4, 8, 22, '2025-01-10'),
(5, 1, 12, '2025-01-10'), (5, 3, 8, '2025-01-08'), (5, 4, 20, '2025-01-12'),
(6, 1, 6, '2025-01-10'), (6, 4, 10, '2025-01-12'), (6, 8, 4, '2025-01-10'),
(7, 1, 40, '2025-01-10'), (7, 2, 35, '2025-01-10'), (7, 3, 25, '2025-01-08'),
(7, 4, 55, '2025-01-12'), (7, 5, 20, '2025-01-09'), (7, 6, 30, '2025-01-11'),
(7, 7, 18, '2025-01-07'), (7, 8, 25, '2025-01-10'),
(8, 1, 10, '2025-01-10'), (8, 4, 15, '2025-01-12'), (8, 6, 8, '2025-01-11'),
(9, 1, 60, '2025-01-10'), (9, 2, 45, '2025-01-10'), (9, 3, 35, '2025-01-08'),
(9, 4, 80, '2025-01-12'), (9, 5, 25, '2025-01-09'), (9, 6, 40, '2025-01-11'),
(9, 7, 20, '2025-01-07'), (9, 8, 30, '2025-01-10'),
(10, 1, 8, '2025-01-10'), (10, 4, 12, '2025-01-12'), (10, 6, 5, '2025-01-11'),
(11, 1, 25, '2025-01-10'), (11, 2, 20, '2025-01-10'), (11, 3, 15, '2025-01-08'),
(11, 4, 30, '2025-01-12'), (11, 7, 10, '2025-01-07'),
(12, 1, 4, '2025-01-10'), (12, 4, 6, '2025-01-12'),
(13, 1, 18, '2025-01-10'), (13, 4, 25, '2025-01-12'), (13, 8, 12, '2025-01-10'),
(14, 1, 10, '2025-01-10'), (14, 4, 15, '2025-01-12'), (14, 6, 8, '2025-01-11'),
(15, 1, 50, '2025-01-10'), (15, 2, 40, '2025-01-10'), (15, 3, 30, '2025-01-08'),
(15, 4, 65, '2025-01-12'), (15, 5, 20, '2025-01-09'), (15, 7, 15, '2025-01-07');
"""

INSERT_VENDAS = """
INSERT INTO vendas (produto_id, loja_id, funcionario_id, quantidade, valor_total, data_venda) VALUES
-- Janeiro 2025
(1, 1, 2, 3, 1469.70, '2025-01-05'),
(4, 1, 2, 2, 1199.80, '2025-01-05'),
(7, 1, 2, 5, 1749.50, '2025-01-06'),
(9, 1, 2, 10, 1199.00, '2025-01-07'),
(1, 2, 5, 4, 1959.60, '2025-01-08'),
(7, 2, 5, 3, 1049.70, '2025-01-08'),
(2, 3, 6, 2, 1459.80, '2025-01-09'),
(4, 3, 6, 3, 1799.70, '2025-01-10'),
(1, 4, 9, 8, 3919.20, '2025-01-10'),
(5, 4, 9, 2, 2599.80, '2025-01-11'),
(7, 4, 9, 6, 2099.40, '2025-01-12'),
(10, 4, 9, 1, 1899.90, '2025-01-12'),
(12, 4, 9, 2, 4999.80, '2025-01-13'),
(11, 7, 14, 3, 2099.70, '2025-01-14'),
(15, 7, 14, 8, 719.20, '2025-01-14'),
(1, 6, 12, 5, 2449.50, '2025-01-15'),
(14, 6, 12, 2, 1999.80, '2025-01-15'),
(13, 8, 15, 4, 1599.60, '2025-01-16'),

-- Fevereiro 2025
(1, 1, 2, 6, 2939.40, '2025-02-03'),
(2, 1, 2, 3, 2189.70, '2025-02-04'),
(7, 1, 2, 4, 1399.60, '2025-02-05'),
(4, 2, 5, 5, 2999.50, '2025-02-06'),
(9, 2, 5, 8, 959.20, '2025-02-06'),
(3, 4, 9, 1, 4899.90, '2025-02-07'),
(6, 4, 9, 2, 3799.80, '2025-02-08'),
(8, 4, 9, 3, 1799.70, '2025-02-10'),
(1, 4, 9, 10, 4899.00, '2025-02-12'),
(7, 3, 6, 4, 1399.60, '2025-02-13'),
(11, 3, 6, 2, 1399.80, '2025-02-14'),
(1, 7, 14, 3, 1469.70, '2025-02-15'),
(4, 7, 14, 2, 1199.80, '2025-02-16'),
(15, 6, 12, 10, 899.00, '2025-02-17'),
(14, 1, 2, 1, 999.90, '2025-02-18'),
(13, 8, 15, 3, 1199.70, '2025-02-20'),

-- Março 2025
(1, 1, 2, 5, 2449.50, '2025-03-03'),
(7, 1, 2, 7, 2449.30, '2025-03-04'),
(2, 1, 2, 4, 2919.60, '2025-03-05'),
(5, 1, 2, 1, 1299.90, '2025-03-06'),
(4, 4, 9, 6, 3599.40, '2025-03-07'),
(1, 4, 9, 12, 5878.80, '2025-03-08'),
(10, 4, 9, 2, 3799.80, '2025-03-10'),
(7, 4, 9, 8, 2799.20, '2025-03-12'),
(9, 3, 6, 6, 719.40, '2025-03-13'),
(11, 3, 6, 4, 2799.60, '2025-03-14'),
(2, 6, 12, 3, 2189.70, '2025-03-15'),
(1, 6, 12, 4, 1959.60, '2025-03-16'),
(12, 4, 9, 1, 2499.90, '2025-03-17'),
(7, 7, 14, 5, 1749.50, '2025-03-18'),
(4, 7, 14, 3, 1799.70, '2025-03-19'),
(13, 8, 15, 5, 1999.50, '2025-03-20'),
(15, 8, 15, 12, 1078.80, '2025-03-21');
"""


# =============================================================
# VIEWS
# -------------------------------------------------------------
# Views analíticas desnormalizadas, pensadas para serem usadas como
# fonte de dados no Azure (Azure AI Search / Azure SQL) para indexação
# e consulta por um agente de IA.
#
# Boas práticas aplicadas para indexação:
# - Cada view expõe uma coluna-chave estável (para o "key field" do índice).
# - Campos legíveis (nome da loja/produto/vendedor) já desnormalizados.
# - Uma view consolidada (vw_ia_fonte_dados) com um campo textual "conteudo"
#   que descreve cada registro em linguagem natural, ideal para busca
#   semântica/vetorial.
# =============================================================
VIEW_STATEMENTS = """
IF OBJECT_ID('dbo.vw_ia_fonte_dados', 'V') IS NOT NULL DROP VIEW dbo.vw_ia_fonte_dados;
IF OBJECT_ID('dbo.vw_vendas_produto_vendedor', 'V') IS NOT NULL DROP VIEW dbo.vw_vendas_produto_vendedor;
IF OBJECT_ID('dbo.vw_produtos_por_loja', 'V') IS NOT NULL DROP VIEW dbo.vw_produtos_por_loja;
IF OBJECT_ID('dbo.vw_estoque_por_produto', 'V') IS NOT NULL DROP VIEW dbo.vw_estoque_por_produto;

-- =============================================================
-- VIEW 1: Total de estoque por produto (agregado em todas as lojas)
-- =============================================================
CREATE VIEW dbo.vw_estoque_por_produto AS
SELECT
    p.id                              AS produto_id,
    p.codigo                          AS produto_codigo,
    p.nome                            AS produto_nome,
    p.categoria                       AS categoria,
    ISNULL(SUM(e.quantidade), 0)      AS estoque_total,
    COUNT(DISTINCT e.loja_id)         AS lojas_com_estoque,
    ISNULL(SUM(e.quantidade), 0) * p.preco_unitario AS valor_estoque_total
FROM produtos p
LEFT JOIN estoque e ON e.produto_id = p.id
GROUP BY p.id, p.codigo, p.nome, p.categoria, p.preco_unitario;

-- =============================================================
-- VIEW 2: Quantidade de produtos por loja
--   - produtos_distintos: nº de SKUs presentes na loja
--   - itens_em_estoque: soma das quantidades
-- =============================================================
CREATE VIEW dbo.vw_produtos_por_loja AS
SELECT
    l.id                              AS loja_id,
    l.nome                            AS loja_nome,
    l.cidade                          AS cidade,
    l.estado                          AS estado,
    l.regiao                          AS regiao,
    COUNT(DISTINCT e.produto_id)      AS produtos_distintos,
    ISNULL(SUM(e.quantidade), 0)      AS itens_em_estoque
FROM lojas l
LEFT JOIN estoque e ON e.loja_id = l.id
GROUP BY l.id, l.nome, l.cidade, l.estado, l.regiao;

-- =============================================================
-- VIEW 3: Total de vendas por produto por vendedor
-- =============================================================
CREATE VIEW dbo.vw_vendas_produto_vendedor AS
SELECT
    v.produto_id                      AS produto_id,
    p.codigo                          AS produto_codigo,
    p.nome                            AS produto_nome,
    p.categoria                       AS categoria,
    v.funcionario_id                  AS funcionario_id,
    f.nome                            AS vendedor_nome,
    f.cargo                           AS vendedor_cargo,
    f.loja_id                         AS loja_id,
    l.nome                            AS loja_nome,
    SUM(v.quantidade)                 AS quantidade_total_vendida,
    SUM(v.valor_total)                AS valor_total_vendido,
    COUNT(*)                          AS numero_de_vendas
FROM vendas v
JOIN produtos p ON p.id = v.produto_id
JOIN funcionarios f ON f.id = v.funcionario_id
JOIN lojas l ON l.id = f.loja_id
GROUP BY v.produto_id, p.codigo, p.nome, p.categoria,
         v.funcionario_id, f.nome, f.cargo, f.loja_id, l.nome;

-- =============================================================
-- VIEW 4: Fonte consolidada para indexação por IA (Azure AI Search)
--   - Uma linha por combinação produto x loja
--   - Coluna-chave estável "id" (produto_id + loja_id)
--   - Campo "conteudo" em linguagem natural para busca semântica/vetorial
-- =============================================================
CREATE VIEW dbo.vw_ia_fonte_dados AS
SELECT
    CAST(p.id AS VARCHAR(10)) + '-' + CAST(l.id AS VARCHAR(10)) AS id,
    p.id                              AS produto_id,
    p.codigo                          AS produto_codigo,
    p.nome                            AS produto_nome,
    p.categoria                       AS categoria,
    p.preco_unitario                  AS preco_unitario,
    l.id                              AS loja_id,
    l.nome                            AS loja_nome,
    l.cidade                          AS cidade,
    l.estado                          AS estado,
    l.regiao                          AS regiao,
    ISNULL(est.quantidade, 0)         AS estoque_na_loja,
    ISNULL(vnd.quantidade_vendida, 0) AS quantidade_vendida,
    ISNULL(vnd.valor_vendido, 0)      AS valor_vendido,
    CONCAT(
        'Produto ', p.nome, ' (código ', p.codigo, ', categoria ', p.categoria,
        ', preço unitário R$ ', CONVERT(VARCHAR(20), p.preco_unitario),
        ') na loja ', l.nome, ' em ', l.cidade, '/', l.estado, ' (região ', l.regiao, '). ',
        'Estoque atual: ', CONVERT(VARCHAR(20), ISNULL(est.quantidade, 0)), ' unidades. ',
        'Total vendido nesta loja: ', CONVERT(VARCHAR(20), ISNULL(vnd.quantidade_vendida, 0)),
        ' unidades, somando R$ ', CONVERT(VARCHAR(20), ISNULL(vnd.valor_vendido, 0)), '.'
    ) AS conteudo
FROM produtos p
CROSS JOIN lojas l
LEFT JOIN (
    SELECT produto_id, loja_id, SUM(quantidade) AS quantidade
    FROM estoque
    GROUP BY produto_id, loja_id
) est ON est.produto_id = p.id AND est.loja_id = l.id
LEFT JOIN (
    SELECT produto_id, loja_id,
           SUM(quantidade) AS quantidade_vendida,
           SUM(valor_total) AS valor_vendido
    FROM vendas
    GROUP BY produto_id, loja_id
) vnd ON vnd.produto_id = p.id AND vnd.loja_id = l.id;
"""


# =============================================================
# TABELA MATERIALIZADA (para indexação incremental no Azure AI Search)
# -------------------------------------------------------------
# O indexer SQL do Azure AI Search precisa de um mecanismo para detectar
# mudanças: SQL integrated change tracking OU uma coluna high-watermark.
# Views não suportam change tracking nem têm uma coluna de "última alteração",
# então materializamos a vw_ia_fonte_dados numa tabela física:
#
#   - Coluna-chave "id" (usada como key field do índice).
#   - Coluna high-watermark "data_atualizacao" (DATETIME2) para refresh
#     incremental via query com "SELECT ... WHERE data_atualizacao > @HighWater".
#   - Change tracking habilitado no banco e na tabela (opção recomendada para
#     detectar deleções via SQL integrated change tracking).
# =============================================================
MATERIALIZED_TABLE_DDL = """
IF OBJECT_ID('dbo.tb_ia_fonte_dados', 'U') IS NOT NULL DROP TABLE dbo.tb_ia_fonte_dados;

CREATE TABLE dbo.tb_ia_fonte_dados (
    id                 VARCHAR(21)    NOT NULL
        CONSTRAINT PK_tb_ia_fonte_dados PRIMARY KEY CLUSTERED,
    produto_id         INT            NOT NULL,
    produto_codigo     NVARCHAR(30)   NOT NULL,
    produto_nome       NVARCHAR(120)  NOT NULL,
    categoria          NVARCHAR(40)   NOT NULL,
    preco_unitario     DECIMAL(10,2)  NOT NULL,
    loja_id            INT            NOT NULL,
    loja_nome          NVARCHAR(100)  NOT NULL,
    cidade             NVARCHAR(60)   NOT NULL,
    estado             NVARCHAR(2)    NOT NULL,
    regiao             NVARCHAR(20)   NOT NULL,
    estoque_na_loja    INT            NOT NULL,
    quantidade_vendida INT            NOT NULL,
    valor_vendido      DECIMAL(18,2)  NOT NULL,
    conteudo           NVARCHAR(MAX)  NOT NULL,
    data_atualizacao   DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME()
);
"""

# =============================================================
# INDEXED VIEW (view materializada com índice) — alternativa a usar a tabela
# -------------------------------------------------------------
# O Azure AI Search, ao usar uma VIEW como "indexed SQL knowledge source",
# EXIGE que ela seja uma indexed view: criada WITH SCHEMABINDING e com um
# UNIQUE CLUSTERED INDEX de coluna única (que vira o document id).
#
# Restrições do SQL Server para indexed views (por isso a vw_ia_fonte_dados
# NÃO pode ser indexada): proíbem CROSS JOIN, OUTER JOIN, subconsultas em
# FROM, ISNULL, CONVERT/CONCAT e várias funções. Portanto criamos uma indexed
# view no grão da tabela 'estoque' (uma linha por produto x loja), usando o
# 'estoque.id' como chave única de coluna única — compatível com o Azure.
#
# Recomendação: para a fonte consolidada com o campo textual 'conteudo',
# prefira apontar o Azure para a TABELA tb_ia_fonte_dados (que já tem PK 'id').
# =============================================================
INDEXED_VIEW_DDL = """
IF OBJECT_ID('dbo.vw_estoque_indexavel', 'V') IS NOT NULL DROP VIEW dbo.vw_estoque_indexavel;
"""

INDEXED_VIEW_CREATE = """
CREATE VIEW dbo.vw_estoque_indexavel
WITH SCHEMABINDING AS
SELECT
    e.id                AS estoque_id,
    e.produto_id        AS produto_id,
    p.codigo            AS produto_codigo,
    p.nome              AS produto_nome,
    p.categoria         AS categoria,
    p.preco_unitario    AS preco_unitario,
    e.loja_id           AS loja_id,
    l.nome              AS loja_nome,
    l.cidade            AS cidade,
    l.estado            AS estado,
    l.regiao            AS regiao,
    e.quantidade        AS estoque_na_loja
FROM dbo.estoque e
JOIN dbo.produtos p ON p.id = e.produto_id
JOIN dbo.lojas l    ON l.id = e.loja_id;
"""

# UNIQUE CLUSTERED INDEX de coluna única -> materializa a view e cria o document id.
INDEXED_VIEW_INDEX = """
CREATE UNIQUE CLUSTERED INDEX IX_vw_estoque_indexavel
    ON dbo.vw_estoque_indexavel (estoque_id);
"""


def create_indexed_view(conn):
    """Cria a indexed view (SCHEMABINDING + unique clustered index).

    Compatível com o requisito do Azure AI Search para usar uma VIEW como
    knowledge source. Cada statement roda em batch próprio.
    """
    # Indexed views exigem estas SET options ON no momento da criação da view
    # e do índice clustered; caso contrário o SQL Server recusa a operação.
    session_options = """
    SET ANSI_NULLS ON;
    SET ANSI_PADDING ON;
    SET ANSI_WARNINGS ON;
    SET ARITHABORT ON;
    SET CONCAT_NULL_YIELDS_NULL ON;
    SET NUMERIC_ROUNDABORT OFF;
    SET QUOTED_IDENTIFIER ON;
    """
    execute_sql(conn, session_options)

    execute_sql(conn, INDEXED_VIEW_DDL)
    conn.commit()
    execute_sql(conn, INDEXED_VIEW_CREATE)
    conn.commit()
    execute_sql(conn, INDEXED_VIEW_INDEX)
    conn.commit()


# Habilita change tracking (SQL integrated change tracking) — opcional, mas é a
# forma recomendada pelo Azure AI Search para detectar inserções/atualizações/
# deleções. Roda em bloco separado porque ALTER DATABASE não pode compartilhar
# batch com outros comandos e é idempotente via checagem em sys.change_tracking_*.
CHANGE_TRACKING_DDL = """
IF NOT EXISTS (SELECT 1 FROM sys.change_tracking_databases WHERE database_id = DB_ID())
    EXEC('ALTER DATABASE CURRENT SET CHANGE_TRACKING = ON (CHANGE_RETENTION = 2 DAYS, AUTO_CLEANUP = ON)');

IF NOT EXISTS (
    SELECT 1 FROM sys.change_tracking_tables
    WHERE object_id = OBJECT_ID('dbo.tb_ia_fonte_dados')
)
    ALTER TABLE dbo.tb_ia_fonte_dados ENABLE CHANGE_TRACKING WITH (TRACK_COLUMNS_UPDATED = OFF);
"""

# Popula/atualiza a tabela materializada a partir da view consolidada.
# Usa MERGE para preservar linhas existentes e atualizar data_atualizacao
# apenas nas linhas que realmente mudaram (evita re-indexação desnecessária).
REFRESH_MATERIALIZED_SQL = """
MERGE dbo.tb_ia_fonte_dados AS destino
USING dbo.vw_ia_fonte_dados AS origem
    ON destino.id = origem.id
WHEN MATCHED AND (
        destino.estoque_na_loja    <> origem.estoque_na_loja
     OR destino.quantidade_vendida <> origem.quantidade_vendida
     OR destino.valor_vendido      <> origem.valor_vendido
     OR destino.preco_unitario     <> origem.preco_unitario
     OR destino.conteudo           <> origem.conteudo
    ) THEN UPDATE SET
        destino.produto_id         = origem.produto_id,
        destino.produto_codigo     = origem.produto_codigo,
        destino.produto_nome       = origem.produto_nome,
        destino.categoria          = origem.categoria,
        destino.preco_unitario     = origem.preco_unitario,
        destino.loja_id            = origem.loja_id,
        destino.loja_nome          = origem.loja_nome,
        destino.cidade             = origem.cidade,
        destino.estado             = origem.estado,
        destino.regiao             = origem.regiao,
        destino.estoque_na_loja    = origem.estoque_na_loja,
        destino.quantidade_vendida = origem.quantidade_vendida,
        destino.valor_vendido      = origem.valor_vendido,
        destino.conteudo           = origem.conteudo,
        destino.data_atualizacao   = SYSUTCDATETIME()
WHEN NOT MATCHED BY TARGET THEN
    INSERT (id, produto_id, produto_codigo, produto_nome, categoria, preco_unitario,
            loja_id, loja_nome, cidade, estado, regiao,
            estoque_na_loja, quantidade_vendida, valor_vendido, conteudo, data_atualizacao)
    VALUES (origem.id, origem.produto_id, origem.produto_codigo, origem.produto_nome,
            origem.categoria, origem.preco_unitario, origem.loja_id, origem.loja_nome,
            origem.cidade, origem.estado, origem.regiao, origem.estoque_na_loja,
            origem.quantidade_vendida, origem.valor_vendido, origem.conteudo, SYSUTCDATETIME())
WHEN NOT MATCHED BY SOURCE THEN
    DELETE;
"""


def refresh_materialized_table(conn):
    """Cria (se necessário) e popula a tabela materializada tb_ia_fonte_dados.

    Executa: DDL da tabela -> change tracking -> MERGE a partir da view.
    Deve ser chamada depois que as views já existem.
    """
    execute_sql(conn, MATERIALIZED_TABLE_DDL)
    conn.commit()

    # Change tracking pode falhar por permissão (precisa de ALTER DATABASE).
    # Tratamos como opcional: se falhar, o refresh incremental por high-watermark
    # (coluna data_atualizacao) ainda funciona.
    try:
        execute_sql(conn, CHANGE_TRACKING_DDL)
        conn.commit()
    except Exception as e:
        print(f"  [WARN] Não foi possível habilitar change tracking: {e}")
        print("         O refresh incremental por high-watermark (data_atualizacao) continua válido.")

    execute_sql(conn, REFRESH_MATERIALIZED_SQL)
    conn.commit()


def split_statements(sql_block: str) -> list[str]:
    """Divide um bloco SQL em statements individuais.

    Ignora linhas de comentário e vazias, quebrando por ';'.
    """
    statements = []
    current = []
    for line in sql_block.split("\n"):
        stripped = line.strip()
        if stripped.startswith("--") or stripped == "":
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []
    if current:
        statements.append("\n".join(current))
    return statements


def execute_sql(conn, sql_block: str):
    """Executa um bloco de SQL statement por statement."""
    cursor = conn.cursor()
    for stmt in split_statements(sql_block):
        stmt = stmt.strip().rstrip(";").strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"  [WARN] Erro ao executar: {stmt[:80]}...")
                print(f"         {e}")
    cursor.close()


def verify_data(conn):
    """Verifica se os dados foram inseridos corretamente."""
    cursor = conn.cursor()
    tables = ["lojas", "funcionarios", "produtos", "estoque", "vendas"]
    print("\n  Verificação de dados:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"    {table}: {count} registros")
    cursor.close()


def verify_views(conn):
    """Verifica se as views foram criadas e retornam dados."""
    cursor = conn.cursor()
    views = [
        "vw_estoque_por_produto",
        "vw_produtos_por_loja",
        "vw_vendas_produto_vendedor",
        "vw_ia_fonte_dados",
        "vw_estoque_indexavel",
        "tb_ia_fonte_dados",
    ]
    print("\n  Verificação de views:")
    for view in views:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {view}")
            count = cursor.fetchone()[0]
            print(f"    {view}: {count} linhas")
        except Exception as e:
            print(f"    {view}: [ERRO] {e}")
    cursor.close()


def main():
    print("=" * 60)
    print("  Inicializando banco de dados SQL Server - Intelbras POC")
    print("=" * 60)

    print(f"\n  Servidor: {SQLSERVER_HOST},{SQLSERVER_PORT}")
    print(f"  Banco de dados: {SQLSERVER_DATABASE}")

    try:
        print("\n  Garantindo que o banco de dados existe...")
        ensure_database()
        print("  Banco de dados disponível!")

        print(f"\n  Criando login '{ROOT_LOGIN}'...")
        create_root_login()
        print(f"  Login '{ROOT_LOGIN}' criado/atualizado (db_owner em {SQLSERVER_DATABASE}).")

        print("\n  Conectando ao SQL Server...")
        conn = get_connection()
        print("  Conexão estabelecida!")
    except pyodbc.Error as e:
        print("\n  [ERRO] Não foi possível conectar ao SQL Server.")
        print(f"         {e}")
        print("\n  Verifique as variáveis SQLSERVER_* no seu .env e se o")
        print("  ODBC Driver for SQL Server está instalado.")
        sys.exit(1)

    print("\n  Criando tabelas...")
    execute_sql(conn, DDL_STATEMENTS)
    print("  Tabelas criadas!")

    print("\n  Inserindo lojas...")
    execute_sql(conn, INSERT_LOJAS)

    print("  Inserindo funcionários...")
    execute_sql(conn, INSERT_FUNCIONARIOS)

    print("  Inserindo produtos...")
    execute_sql(conn, INSERT_PRODUTOS)

    print("  Inserindo estoque...")
    execute_sql(conn, INSERT_ESTOQUE)

    print("  Inserindo vendas...")
    execute_sql(conn, INSERT_VENDAS)

    conn.commit()

    print("\n  Criando views (fonte de dados para IA/Azure)...")
    execute_sql(conn, VIEW_STATEMENTS)
    conn.commit()
    print("  Views criadas!")

    print("\n  Criando indexed view (SCHEMABINDING + unique clustered index)...")
    try:
        create_indexed_view(conn)
        print("  Indexed view vw_estoque_indexavel criada!")
    except Exception as e:
        print(f"  [WARN] Não foi possível criar a indexed view: {e}")

    print("\n  Materializando tabela para indexação incremental (Azure AI Search)...")
    refresh_materialized_table(conn)
    print("  Tabela tb_ia_fonte_dados criada e populada!")

    verify_data(conn)
    verify_views(conn)

    conn.close()
    print("\n  Banco de dados inicializado com sucesso!")
    print("=" * 60)


if __name__ == "__main__":
    main()
