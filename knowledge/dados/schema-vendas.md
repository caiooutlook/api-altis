---
type: dataset
display_name: "Tabela: vendas"
description: "Registro de vendas realizadas por funcionário, loja e produto"
tags: [banco-de-dados, tabela, vendas, faturamento, transacoes, comercial]
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

# Tabela: vendas

## Descrição

Registro de todas as vendas realizadas. Cada venda vincula um produto, uma loja e o funcionário que realizou a transação. Contém quantidade vendida, valor total e data. É a principal tabela para análises comerciais e de desempenho.

## Schema

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | Identificador da venda |
| produto_id | INT | NOT NULL, FK → produtos.id | Produto vendido |
| loja_id | INT | NOT NULL, FK → lojas.id | Loja onde ocorreu a venda |
| funcionario_id | INT | NOT NULL, FK → funcionarios.id | Vendedor que realizou |
| quantidade | INT | NOT NULL | Quantidade de unidades vendidas |
| valor_total | DECIMAL(10,2) | NOT NULL | Valor total da transação (quantidade × preço) |
| data_venda | DATE | NOT NULL | Data em que a venda ocorreu |

## Relacionamentos

- `vendas.produto_id` → `produtos.id` (N:1)
- `vendas.loja_id` → `lojas.id` (N:1)
- `vendas.funcionario_id` → `funcionarios.id` (N:1)

## Período de dados

Os dados de vendas cobrem **Janeiro a Março de 2025** (Q1 2025):
- Janeiro: 18 transações
- Fevereiro: 16 transações
- Março: 17 transações
- Total: 51 transações

## Métricas disponíveis

| Métrica | Como calcular |
|---------|---------------|
| Faturamento total | `SUM(valor_total)` |
| Ticket médio | `AVG(valor_total)` |
| Unidades vendidas | `SUM(quantidade)` |
| Vendas por mês | `GROUP BY MONTH(data_venda)` |
| Vendas por loja | `GROUP BY loja_id` |
| Vendas por vendedor | `GROUP BY funcionario_id` |
| Vendas por categoria | `JOIN produtos` + `GROUP BY categoria` |
| Ranking de produtos | `GROUP BY produto_id ORDER BY SUM(quantidade) DESC` |

## Regras de negócio

- `valor_total` = `quantidade × preco_unitario` no momento da venda
- Cada registro representa uma transação (pode conter múltiplas unidades do mesmo produto)
- Um funcionário só registra vendas na loja onde está alocado
- Não há devoluções ou cancelamentos neste modelo simplificado

## Queries comuns

- Faturamento total do período: `SELECT SUM(valor_total) as faturamento FROM vendas`
- Faturamento por mês: `SELECT MONTH(data_venda) as mes, SUM(valor_total) as total FROM vendas GROUP BY MONTH(data_venda) ORDER BY mes`
- Top 5 produtos mais vendidos (unidades): `SELECT p.nome, SUM(v.quantidade) as unidades FROM vendas v JOIN produtos p ON v.produto_id = p.id GROUP BY p.nome ORDER BY unidades DESC LIMIT 5`
- Vendedor que mais faturou: `SELECT f.nome, SUM(v.valor_total) as total FROM vendas v JOIN funcionarios f ON v.funcionario_id = f.id GROUP BY f.nome ORDER BY total DESC LIMIT 5`
- Faturamento por loja: `SELECT l.nome, SUM(v.valor_total) as total FROM vendas v JOIN lojas l ON v.loja_id = l.id GROUP BY l.nome ORDER BY total DESC`
- Faturamento por categoria: `SELECT p.categoria, SUM(v.valor_total) as total FROM vendas v JOIN produtos p ON v.produto_id = p.id GROUP BY p.categoria ORDER BY total DESC`
