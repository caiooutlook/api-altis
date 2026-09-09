---
type: dataset
display_name: "Tabela: lojas"
description: "Cadastro das lojas/filiais da Intelbras com localização geográfica"
tags: [banco-de-dados, tabela, lojas, filiais, localizacao]
category: Dados
lifecycle: active
verified: human-reviewed
sources:
  - uri: "jdbc:h2:./data/intelbras_db"
    type: database
    credibility:
      author: "Equipe de TI Intelbras"
      last_modified: "2025-01-12"
---

# Tabela: lojas

## Descrição

Armazena o cadastro de todas as lojas/filiais da Intelbras. Cada loja possui uma localização geográfica (cidade, estado, região) e é o ponto de venda e estoque de produtos.

## Schema

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| id | INT | PRIMARY KEY | Identificador único da loja |
| nome | VARCHAR(100) | NOT NULL | Nome completo da loja (ex: "Intelbras Florianópolis Centro") |
| cidade | VARCHAR(60) | NOT NULL | Cidade onde a loja está localizada |
| estado | VARCHAR(2) | NOT NULL | Sigla do estado (UF) |
| regiao | VARCHAR(20) | NOT NULL | Região geográfica: Sul, Sudeste, Nordeste, Centro-Oeste |
| telefone | VARCHAR(20) | nullable | Telefone de contato da loja |

## Relacionamentos

- `lojas.id` é referenciada por `funcionarios.loja_id` (1:N — uma loja tem vários funcionários)
- `lojas.id` é referenciada por `estoque.loja_id` (1:N — uma loja tem estoque de vários produtos)
- `lojas.id` é referenciada por `vendas.loja_id` (1:N — uma loja realiza várias vendas)

## Dados atuais

A empresa possui 8 lojas cadastradas distribuídas em 4 regiões:

| Região | Lojas |
|--------|-------|
| Sul | Florianópolis Centro, São José (SC), Curitiba (PR) |
| Sudeste | São Paulo Paulista (SP), Campinas (SP), Belo Horizonte (MG) |
| Nordeste | Recife (PE) |
| Centro-Oeste | Brasília (DF) |

## Queries comuns

- Listar lojas por região: `SELECT * FROM lojas WHERE regiao = 'Sul'`
- Contar lojas por estado: `SELECT estado, COUNT(*) FROM lojas GROUP BY estado`
