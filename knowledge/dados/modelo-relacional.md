---
type: dataset
display_name: "Modelo Relacional - Banco Intelbras"
description: "Visão geral do modelo de dados relacional do sistema de vendas Intelbras"
tags: [banco-de-dados, modelo, relacional, visao-geral, er]
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

# Modelo Relacional - Sistema de Vendas Intelbras

## Visão Geral

O banco de dados do sistema de vendas da Intelbras é composto por 5 tabelas que cobrem a operação comercial da empresa: cadastro de lojas, funcionários, produtos, controle de estoque e registro de vendas.

## Diagrama ER (Entidade-Relacionamento)

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│    lojas     │       │  funcionarios    │       │   produtos   │
├──────────────┤       ├──────────────────┤       ├──────────────┤
│ id (PK)      │◄──┐   │ id (PK)          │       │ id (PK)      │
│ nome         │   │   │ nome             │       │ codigo (UK)  │
│ cidade       │   ├───│ loja_id (FK)     │       │ nome         │
│ estado       │   │   │ cargo            │       │ categoria    │
│ regiao       │   │   │ email            │       │ preco_unit.  │
│ telefone     │   │   │ data_admissao    │       │ descricao    │
└──────────────┘   │   │ salario          │       └──────────────┘
       ▲           │   └──────────────────┘              ▲
       │           │            ▲                        │
       │           │            │                        │
       │    ┌──────┴────────────┴───────────────┐       │
       │    │            vendas                  │       │
       │    ├────────────────────────────────────┤       │
       │    │ id (PK)                            │       │
       ├────│ loja_id (FK)                       │       │
       │    │ funcionario_id (FK)                │       │
       │    │ produto_id (FK) ───────────────────┼───────┘
       │    │ quantidade                         │
       │    │ valor_total                        │
       │    │ data_venda                         │
       │    └────────────────────────────────────┘
       │
       │    ┌────────────────────────────────────┐
       │    │            estoque                  │
       │    ├────────────────────────────────────┤
       │    │ id (PK)                            │
       └────│ loja_id (FK)                       │
            │ produto_id (FK) ───────────────────┼───── produtos.id
            │ quantidade                         │
            │ ultima_atualizacao                 │
            └────────────────────────────────────┘
```

## Resumo das tabelas

| Tabela | Registros | Propósito |
|--------|-----------|-----------|
| lojas | 8 | Filiais da Intelbras em 4 regiões do Brasil |
| funcionarios | 15 | Colaboradores (gerentes, vendedores, técnicos) |
| produtos | 15 | Catálogo de produtos em 6 categorias |
| estoque | 68 | Saldo atual por produto × loja |
| vendas | 51 | Transações de Jan-Mar 2025 |

## Padrões de consulta típicos

### Análise comercial
- Faturamento por período, loja, vendedor ou categoria
- Ranking de produtos mais vendidos
- Ticket médio por loja ou vendedor
- Comparativo mensal de vendas

### Disponibilidade
- Estoque atual de um produto em todas as lojas
- Produtos sem estoque (esgotados) por loja
- Lojas que não comercializam determinado produto

### Informações operacionais
- Lista de funcionários por loja ou cargo
- Contato e localização de lojas
- Dados de um produto específico (preço, categoria)

## Tecnologia

- **SGBD:** H2 Database (modo embedded)
- **Dialeto SQL:** Compatível com SQL ANSI padrão
- **Conexão:** JDBC via JayDeBeApi (Python)
- **Funções de data H2:** `MONTH()`, `YEAR()`, `DATEDIFF()`, `CURRENT_DATE`
