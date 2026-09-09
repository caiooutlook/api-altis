---
type: dataset
display_name: "Tabela: produtos"
description: "Catálogo de produtos Intelbras disponíveis para venda"
tags: [banco-de-dados, tabela, produtos, catalogo, skus]
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

# Tabela: produtos

## Descrição

Catálogo de produtos Intelbras disponíveis no sistema de vendas. Cada produto possui um código único (SKU), nome, categoria, preço unitário e descrição resumida.

## Schema

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| id | INT | PRIMARY KEY | Identificador interno do produto |
| codigo | VARCHAR(30) | NOT NULL, UNIQUE | Código/SKU do produto (ex: "VIP-1230-D") |
| nome | VARCHAR(120) | NOT NULL | Nome comercial completo |
| categoria | VARCHAR(40) | NOT NULL | Categoria do produto (ver valores abaixo) |
| preco_unitario | DECIMAL(10,2) | NOT NULL | Preço de venda unitário em R$ |
| descricao | VARCHAR(500) | nullable | Descrição técnica resumida |

## Categorias de produtos

| Categoria | Exemplos | Faixa de preço |
|-----------|----------|----------------|
| Câmeras | VIP 1230 D, VIP 3230 B, VIP 7230 EF | R$ 489 a R$ 4.899 |
| Gravadores | MHDX 1004-C, MHDX 3008-C, NVD 1232 | R$ 599 a R$ 1.899 |
| Redes | Wi-Force W6 1500, AP 1350 AC, SF 800 Q+ | R$ 119 a R$ 599 |
| Alarmes | AMT 8000, AMT 4010 Smart, SS 3530 MF W | R$ 89 a R$ 1.899 |
| Comunicação | XPE 3200 IP, TIP 125i | R$ 399 a R$ 2.499 |
| Controle de Acesso | ELC 5001 RF | R$ 999 |

## Relacionamentos

- `produtos.id` é referenciada por `estoque.produto_id` (1:N — um produto tem estoque em várias lojas)
- `produtos.id` é referenciada por `vendas.produto_id` (1:N — um produto aparece em várias vendas)

## Dados atuais

- 15 produtos cadastrados em 6 categorias
- Preço mínimo: R$ 89,90 (Sensor SS 3530 MF W)
- Preço máximo: R$ 4.899,90 (Câmera Speed Dome VIP 7230 EF)
- Preço médio: ~R$ 1.177

## Queries comuns

- Produtos por categoria: `SELECT codigo, nome, preco_unitario FROM produtos WHERE categoria = 'Câmeras' ORDER BY preco_unitario`
- Produto mais caro: `SELECT nome, preco_unitario FROM produtos ORDER BY preco_unitario DESC LIMIT 1`
- Buscar por código: `SELECT * FROM produtos WHERE codigo = 'VIP-1230-D'`
