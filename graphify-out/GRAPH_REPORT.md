# Graph Report - DMED  (2026-10-29)

## Corpus Check
- 28 files · ~17,226 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 21 file(s) not represented in the graph (top: .csv 12, (none) 5, .toml 1)

## Summary
- 460 nodes · 1081 edges · 17 communities (13 shown, 4 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 93 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `94ac7014`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- conftest.py
- test_paginas.py
- config.py
- test_funcoes_puras.py
- paginas/arquivo_dmed.py
- exibir_consulta
- pandas
- ler_cache
- manual_de_regras.md
- validacao.py
- dmed
- hooks
- main.py
- DMED COSEMI
- ratear_aba

## God Nodes (most connected - your core abstractions)
1. `Ocorrencia` - 26 edges
2. `formatar_cpf()` - 21 edges
3. `exibir_consulta()` - 19 edges
4. `processar_descontos()` - 18 edges
5. `Planilha` - 17 edges
6. `Consulta` - 17 edges
7. `processar_mensalidades()` - 16 edges
8. `ler_valor_monetario()` - 15 edges
9. `Chaves` - 15 edges
10. `test_consulta_por_cpf()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `test_valor_para_soma_descarta_o_sinal()` --calls--> `valor_para_soma()`  [EXTRACTED]
  tests/test_funcoes_puras.py → src/dmed/backend/informe_pdf.py
- `test_ocorrencia_mantem_o_texto_do_relatorio()` --uses--> `Severidade`  [INFERRED]
  tests/test_funcoes_puras.py → src/dmed/backend/ocorrencias.py
- `test_ocorrencia_mantem_o_texto_do_relatorio()` --uses--> `Ocorrencia`  [INFERRED]
  tests/test_funcoes_puras.py → src/dmed/backend/ocorrencias.py
- `linhas()` --uses--> `Ocorrencia`  [INFERRED]
  tests/test_processamento.py → src/dmed/backend/ocorrencias.py
- `consulta()` --uses--> `Chaves`  [INFERRED]
  tests/test_paginas.py → src/dmed/frontend/componentes.py

## Import Cycles
- None detected.

## Communities (17 total, 4 thin omitted)

### Community 0 - "conftest.py"
Cohesion: 0.10
Nodes (8): ambiente(), esperado(), monta_pasta(), monta_xlsx(), pytest_addoption(), pytest_configure(), pytest_unconfigure(), sem_rede()

### Community 1 - "test_paginas.py"
Cohesion: 0.14
Nodes (25): abre_dmed(), abre_dmed_autenticado(), abre_inicio(), botao(), consulta(), entra(), preenche_responsavel(), rotulos_de_download() (+17 more)

### Community 2 - "config.py"
Cohesion: 0.10
Nodes (17): agora(), ConfiguracaoAusente, destino_planilha(), pasta_cache(), pasta_dados(), pasta_descontos(), pasta_despesas(), pasta_mensalidades() (+9 more)

### Community 3 - "test_funcoes_puras.py"
Cohesion: 0.17
Nodes (13): _exibicao_antiga(), _moeda_antiga(), test_codigo_dependencia(), test_formatar_cpf(), test_formatar_moeda_igual_a_formula_antiga(), test_formatar_valor_dmed(), test_ler_valor_monetario(), test_meses_ativos() (+5 more)

### Community 4 - "paginas/arquivo_dmed.py"
Cohesion: 0.08
Nodes (26): alternador_de_tema(), aplicar_identidade_visual(), botao_download(), cartao(), Chaves, Etapas, heroi(), plural() (+18 more)

### Community 5 - "exibir_consulta"
Cohesion: 0.06
Nodes (29): _despesas_por_titular(), gerar_arquivo_dmed(), _montar(), ano_calendario(), ano_entrega(), _abater_negativos(), _agrupar(), _ajustar_ao_desconto() (+21 more)

### Community 6 - "pandas"
Cohesion: 0.06
Nodes (36): codigo_dependencia(), registros_do_grupo(), _base_descontos(), BaseDescontos, _somar(), _consolidar(), padronizar(), processar_descontos() (+28 more)

### Community 7 - "ler_cache"
Cohesion: 0.21
Nodes (6): _carregar(), _versao(), assinatura(), CacheIndisponivel, ler_cache(), _ler_csv()

### Community 8 - "manual_de_regras.md"
Cohesion: 0.05
Nodes (43): Análise da Planilha, Apresentação Final, Armazenamento, Benefícios do Sistema:, Benefícios do Sistema:, BUSCA DESCONTOS, BUSCA DESPESAS, BUSCA MENSALIDADES (+35 more)

### Community 9 - "validacao.py"
Cohesion: 0.11
Nodes (14): Responsavel, MensalidadesIndisponiveis, formulario_de_consulta(), cpf_com_mascara(), CpfConsultado, ler_cpf_da_consulta(), somente_digitos(), validar_responsavel() (+6 more)

### Community 13 - "hooks"
Cohesion: 0.15
Nodes (12): exclude, args, entry, exclude, id, language, name, types_or (+4 more)

### Community 15 - "DMED COSEMI"
Cohesion: 0.20
Nodes (9): Dados, Deploy, DMED COSEMI, Estrutura, Execução, Instalação, Licença, Requisitos (+1 more)

### Community 19 - "ratear_aba"
Cohesion: 0.22
Nodes (3): _atribuir_titulares(), meses_ativos(), ratear_aba()

## Knowledge Gaps
- **1 isolated node(s):** `dmed`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 186 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Chaves` connect `paginas/arquivo_dmed.py` to `validacao.py`, `test_paginas.py`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Ocorrencia` (e.g. with `gerar_arquivo_dmed()` and `padronizar()`) actually correct?**
  _`Ocorrencia` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `dmed` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `conftest.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09971509971509972 - nodes in this community are weakly interconnected._
- **Why does `formatar_cpf()` connect `pandas` to `validacao.py`, `ratear_aba`, `exibir_consulta`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `formatar_cpf()` (e.g. with `_montar()` and `_base_descontos()`) actually correct?**
  _`formatar_cpf()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_paginas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13903743315508021 - nodes in this community are weakly interconnected._