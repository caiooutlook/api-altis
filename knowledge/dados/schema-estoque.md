---
type: dataset
display_name: "Tabela: estoque"
description: "Controle de estoque de produtos por loja"
tags: [banco-de-dados, tabela, estoque, inventario, disponibilidade]
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

# Tabela: estoque

## Descrição

Controla a quantidade disponível de cada produto em cada loja. A relação é produto × loja, ou seja, um mesmo produto pode ter quantidades diferentes em lojas distintas. Nem todas as lojas possuem todos os produtos em estoque.

## Schema

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | Identificador do registro |
| produto_id | INT | NOT NULL, FK → produtos.id | Produto em estoque |
| loja_id | INT | NOT NULL, FK → lojas.id | Loja onde o estoque está |
| quantidade | INT | NOT NULL, DEFAULT 0 | Quantidade disponível (unidades) |
| ultima_atualizacao | DATE | nullable | Data da última atualização do estoque |

## Relacionamentos

- `estoque.produto_id` → `produtos.id` (N:1)
- `estoque.loja_id` → `lojas.id` (N:1)
- Chave lógica composta: (produto_id, loja_id) — um registro por combinação

## Regras de negócio

- Se não existe registro de estoque para um produto em uma loja, significa que aquele produto **não é comercializado** naquela loja
- Quantidade zero significa que o produto é comercializado mas está temporariamente sem estoque
- A tabela não mantém histórico — apenas o saldo atual

## Dados atuais

- 68 registros de estoque (nem toda combinação produto×loja existe)
- Produtos com maior distribuição (presentes em todas as 8 lojas): VIP 1230 D, MHDX 1004-C, Wi-Force W6 1500, SF 800 Q+
- Produtos com distribuição limitada: VIP 7230 EF (3 lojas), XPE 3200 IP (2 lojas), NVD 1232 (3 lojas)
- Última atualização: entre 07/01/2025 e 12/01/2025

## Queries comuns

- Estoque de um produto em todas as lojas: `SELECT l.nome, e.quantidade FROM estoque e JOIN lojas l ON e.loja_id = l.id JOIN produtos p ON e.produto_id = p.id WHERE p.codigo = 'VIP-1230-D'`
- Produtos sem estoque em uma loja: `SELECT p.nome FROM produtos p JOIN estoque e ON p.id = e.produto_id JOIN lojas l ON e.loja_id = l.id WHERE l.cidade = 'São Paulo' AND e.quantidade = 0`
- Estoque total por produto: `SELECT p.nome, SUM(e.quantidade) as total FROM estoque e JOIN produtos p ON e.produto_id = p.id GROUP BY p.nome ORDER BY total DESC`
- Lojas que NÃO possuem um produto: `SELECT l.nome FROM lojas l WHERE l.id NOT IN (SELECT e.loja_id FROM estoque e JOIN produtos p ON e.produto_id = p.id WHERE p.codigo = 'VIP-7230-EF')`
