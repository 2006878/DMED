# Graph Report - DMED  (2026-10-28)

## Corpus Check
- 25 files · ~14,904 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .csv 12, (none) 5, .toml 1)

## Summary
- 386 nodes · 849 edges · 15 communities (12 shown, 3 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 57 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `20fa713a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- conftest.py
- test_paginas.py
- config.py
- test_funcoes_puras.py
- informe_irpf.py
- consulta.py
- despesas.py
- fontes.py
- manual_de_regras.md
- backend/arquivo_dmed.py
- dmed
- hooks
- DMED COSEMI

## God Nodes (most connected - your core abstractions)
1. `Ocorrencia` - 26 edges
2. `formatar_cpf()` - 20 edges
3. `processar_descontos()` - 17 edges
4. `Consulta` - 16 edges
5. `processar_mensalidades()` - 15 edges
6. `test_consulta_por_cpf()` - 15 edges
7. `Planilha` - 14 edges
8. `ler_valor_monetario()` - 14 edges
9. `gerar_arquivo_dmed()` - 13 edges
10. `processar_despesas()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `test_cache_existente_nao_e_reprocessado()` --uses--> `Consulta`  [INFERRED]
  tests/test_processamento.py → src/dmed/backend/consulta.py
- `test_pdf_nao_altera_a_tabela()` --uses--> `Consulta`  [INFERRED]
  tests/test_processamento.py → src/dmed/backend/consulta.py
- `test_consulta_por_cpf()` --indirect_call--> `valor_para_soma()`  [INFERRED]
  tests/test_processamento.py → src/dmed/backend/informe_pdf.py
- `test_ocorrencia_mantem_o_texto_do_relatorio()` --uses--> `Severidade`  [INFERRED]
  tests/test_funcoes_puras.py → src/dmed/backend/ocorrencias.py
- `test_ocorrencia_mantem_o_texto_do_relatorio()` --uses--> `Ocorrencia`  [INFERRED]
  tests/test_funcoes_puras.py → src/dmed/backend/ocorrencias.py

## Import Cycles
- None detected.

## Communities (15 total, 3 thin omitted)

### Community 0 - "conftest.py"
Cohesion: 0.08
Nodes (10): ambiente(), csv_texto(), esperado(), monta_pasta(), monta_xlsx(), normaliza_pdf(), pytest_addoption(), pytest_configure() (+2 more)

### Community 1 - "test_paginas.py"
Cohesion: 0.18
Nodes (13): abre_dmed_autenticado(), abre_inicio(), botao(), campo(), test_dmed_cpf_incompleto_mostra_erro_sem_quebrar(), test_dmed_exibe_formulario_e_manual(), test_dmed_gera_arquivo_com_relatorio_de_erros(), test_dmed_sem_senha_configurada() (+5 more)

### Community 2 - "config.py"
Cohesion: 0.09
Nodes (18): exportar_ids_do_drive(), ConfiguracaoAusente, destino_planilha(), pasta_cache(), pasta_dados(), pasta_descontos(), pasta_despesas(), pasta_mensalidades() (+10 more)

### Community 3 - "test_funcoes_puras.py"
Cohesion: 0.09
Nodes (19): ano_calendario(), formatar_numero(), gerar_informe_pdf(), _linhas_nome_valor(), valor_para_exibicao(), valor_para_soma(), _exibicao_antiga(), _moeda_antiga() (+11 more)

### Community 4 - "informe_irpf.py"
Cohesion: 0.12
Nodes (14): agora(), MensalidadesIndisponiveis, cartao(), Chaves, configurar_pagina(), escapar(), exibir_logo(), html() (+6 more)

### Community 5 - "consulta.py"
Cohesion: 0.10
Nodes (17): _abater_negativos(), _agrupar(), _ajustar_ao_desconto(), _base_descontos(), _base_despesas(), _base_mensalidades(), BaseDescontos, BaseDespesas (+9 more)

### Community 6 - "despesas.py"
Cohesion: 0.07
Nodes (25): _consolidar(), padronizar(), processar_descontos(), _consolidar(), _cpf_do_responsavel(), _ler_csv_avulso(), _ler_pasta(), padronizar() (+17 more)

### Community 7 - "fontes.py"
Cohesion: 0.11
Nodes (11): _carregar(), _versao(), arquivos_da_pasta(), assinatura(), baixar_planilha(), baixar_planilhas_do_drive(), cache_existe(), CacheIndisponivel (+3 more)

### Community 8 - "manual_de_regras.md"
Cohesion: 0.05
Nodes (43): Análise da Planilha, Apresentação Final, Armazenamento, Benefícios do Sistema:, Benefícios do Sistema:, BUSCA DESCONTOS, BUSCA DESPESAS, BUSCA MENSALIDADES (+35 more)

### Community 9 - "backend/arquivo_dmed.py"
Cohesion: 0.13
Nodes (10): codigo_dependencia(), _despesas_por_titular(), gerar_arquivo_dmed(), _montar(), registros_do_grupo(), Responsavel, ano_entrega(), _normalizar_coluna() (+2 more)

### Community 13 - "hooks"
Cohesion: 0.15
Nodes (12): exclude, args, entry, exclude, id, language, name, types_or (+4 more)

### Community 15 - "DMED COSEMI"
Cohesion: 0.20
Nodes (9): Dados, Deploy, DMED COSEMI, Estrutura, Execução, Instalação, Licença, Requisitos (+1 more)

## Knowledge Gaps
- **1 isolated node(s):** `dmed`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 164 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Ocorrencia` connect `despesas.py` to `backend/arquivo_dmed.py`, `test_funcoes_puras.py`, `informe_irpf.py`, `consulta.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `Ocorrencia` (e.g. with `gerar_arquivo_dmed()` and `padronizar()`) actually correct?**
  _`Ocorrencia` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `dmed` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `conftest.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08387096774193549 - nodes in this community are weakly interconnected._
- **Why does `Consulta` connect `consulta.py` to `backend/arquivo_dmed.py`, `config.py`, `informe_irpf.py`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `formatar_cpf()` (e.g. with `_montar()` and `_base_descontos()`) actually correct?**
  _`formatar_cpf()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `config.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09102564102564102 - nodes in this community are weakly interconnected._