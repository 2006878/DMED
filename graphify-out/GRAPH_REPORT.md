# Graph Report - DMED  (2026-10-28)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 125 nodes · 253 edges · 13 communities (8 shown, 5 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 15 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `19275a0e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- conftest.py
- test_paginas.py
- test_processamento.py
- test_funcoes_puras.py
- arquivo_dmed.py
- processamento.py
- informe_irpf.py
- os
- processa_despesas
- generate_pdf
- dmed

## God Nodes (most connected - your core abstractions)
1. `format_cpf()` - 12 edges
2. `create_dmed_content()` - 11 edges
3. `processa_despesas()` - 11 edges
4. `processa_descontos()` - 10 edges
5. `processa_mensalidades()` - 10 edges
6. `busca_dados_descontos()` - 9 edges
7. `busca_dados_despesas()` - 9 edges
8. `parse_valor_monetario()` - 9 edges
9. `busca_dados_mensalidades()` - 9 edges
10. `abre_inicio()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `test_consulta_por_cpf()` --calls--> `csv_texto()`  [EXTRACTED]
  tests/test_processamento.py → tests/conftest.py
- `test_consulta_por_cpf()` --calls--> `normaliza_pdf()`  [EXTRACTED]
  tests/test_processamento.py → tests/conftest.py

## Import Cycles
- None detected.

## Communities (13 total, 5 thin omitted)

### Community 0 - "conftest.py"
Cohesion: 0.10
Nodes (8): ambiente(), esperado(), monta_pasta(), monta_xlsx(), pytest_addoption(), pytest_configure(), pytest_unconfigure(), sem_rede()

### Community 1 - "test_paginas.py"
Cohesion: 0.17
Nodes (11): abre_dmed_autenticado(), abre_inicio(), botao(), campo(), test_dmed_exibe_formulario_e_manual(), test_dmed_gera_arquivo_com_relatorio_de_erros(), test_dmed_senha_incorreta(), test_inicio_consulta_cpf() (+3 more)

### Community 2 - "test_processamento.py"
Cohesion: 0.20
Nodes (7): csv_texto(), normaliza_pdf(), linhas(), test_arquivo_dmed(), test_cache_existente_nao_e_reprocessado(), test_consulta_por_cpf(), test_processamento_das_planilhas()

### Community 3 - "test_funcoes_puras.py"
Cohesion: 0.20
Nodes (7): test_calculate_active_months(), test_format_cpf(), test_format_valor(), test_get_dependent_code(), test_normalize_name(), test_parse_valor_monetario(), test_process_group()

### Community 5 - "processamento.py"
Cohesion: 0.30
Nodes (6): calculate_active_months(), create_dmed_content(), format_valor(), get_dependent_code(), normalize_name(), process_group()

### Community 6 - "informe_irpf.py"
Cohesion: 0.61
Nodes (6): busca_dados_descontos(), busca_dados_despesas(), format_cpf(), parse_valor_monetario(), processa_descontos(), padroniza_e_valida_df()

### Community 7 - "os"
Cohesion: 0.38
Nodes (4): baixar_e_atualizar_planilhas(), busca_dados_mensalidades(), format_currency(), processa_mensalidades()

### Community 8 - "processa_despesas"
Cohesion: 1.00
Nodes (3): processa_despesas(), normaliza_coluna(), padroniza_df()

## Knowledge Gaps
- **1 isolated node(s):** `dmed`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 43 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `normaliza_pdf()` connect `test_processamento.py` to `conftest.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `format_cpf()` (e.g. with `busca_dados_descontos()` and `busca_dados_despesas()`) actually correct?**
  _`format_cpf()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `dmed` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `conftest.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10461538461538461 - nodes in this community are weakly interconnected._
- **Are the 2 inferred relationships involving `processa_despesas()` (e.g. with `format_cpf()` and `parse_valor_monetario()`) actually correct?**
  _`processa_despesas()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `processa_descontos()` (e.g. with `format_cpf()` and `parse_valor_monetario()`) actually correct?**
  _`processa_descontos()` has 2 INFERRED edges - model-reasoned connections that need verification._