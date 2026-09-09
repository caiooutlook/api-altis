---
type: dataset
display_name: "Tabela: funcionarios"
description: "Cadastro dos funcionários da Intelbras vinculados a lojas"
tags: [banco-de-dados, tabela, funcionarios, rh, colaboradores]
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

# Tabela: funcionarios

## Descrição

Cadastro dos colaboradores da Intelbras que atuam nas lojas. Cada funcionário está vinculado a uma loja e possui um cargo definido. Contém dados de RH como data de admissão e salário.

## Schema

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| id | INT | PRIMARY KEY | Identificador único do funcionário |
| nome | VARCHAR(100) | NOT NULL | Nome completo |
| cargo | VARCHAR(60) | NOT NULL | Cargo atual (ver valores abaixo) |
| loja_id | INT | NOT NULL, FK → lojas.id | Loja onde o funcionário trabalha |
| email | VARCHAR(100) | nullable | E-mail corporativo (@intelbras.com.br) |
| data_admissao | DATE | nullable | Data de admissão na empresa |
| salario | DECIMAL(10,2) | nullable | Salário mensal bruto em R$ |

## Valores de cargo

| Cargo | Descrição |
|-------|-----------|
| Gerente de Loja | Responsável pela operação da loja. Um por loja. |
| Vendedor / Vendedora | Realiza vendas diretamente ao cliente. |
| Técnico de Suporte / Técnica de Suporte | Atende dúvidas técnicas e auxilia pós-venda. |

## Relacionamentos

- `funcionarios.loja_id` → `lojas.id` (N:1 — vários funcionários por loja)
- `funcionarios.id` é referenciada por `vendas.funcionario_id` (1:N — um funcionário registra várias vendas)

## Dados atuais

- 15 funcionários cadastrados
- Distribuídos em 6 das 8 lojas
- 5 gerentes, 7 vendedores, 3 técnicos de suporte
- Admissões de 2016 a 2023
- Faixa salarial: R$ 3.900 a R$ 9.500

## Queries comuns

- Funcionários de uma loja: `SELECT f.nome, f.cargo FROM funcionarios f JOIN lojas l ON f.loja_id = l.id WHERE l.cidade = 'Curitiba'`
- Gerentes: `SELECT f.nome, l.nome as loja FROM funcionarios f JOIN lojas l ON f.loja_id = l.id WHERE f.cargo = 'Gerente de Loja'`
- Tempo de empresa: `SELECT nome, DATEDIFF(MONTH, data_admissao, CURRENT_DATE) as meses FROM funcionarios ORDER BY meses DESC`
