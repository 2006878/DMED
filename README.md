# DMED COSEMI

Aplicação [Streamlit](https://streamlit.io/) da COSEMI com duas páginas:

- **Informe de plano de saúde (IRPF):** consulta pelo CPF do titular e gera o PDF do informe do ano-calendário anterior.
- **Arquivo DMED:** gera o arquivo `.DEC` da DMED para a Receita Federal, com relatório das inconsistências encontradas nas planilhas. Protegida por senha.

## Requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/), que também instala um Python compatível (3.11 ou mais novo, conforme o `pyproject.toml`).

## Instalação

```sh
uv sync
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
uv run pre-commit install
```

Preencha o `.streamlit/secrets.toml` (não versionado): a senha da página do arquivo DMED e, na seção `[drive]`, os IDs das planilhas de mensalidades e de descontos no Google Drive.

## Execução

```sh
uv run streamlit run main.py
```

A aplicação abre em <http://localhost:8501>.

## Testes e qualidade

```sh
uv run pytest                          # testes
uv run pytest --cov                    # testes com cobertura
uv run ruff check .                    # lint
uv run ruff format .                   # formatação
uv run mypy                            # tipos
uv run pre-commit run --all-files      # todos os hooks do pre-commit
```

Os testes rodam sobre planilhas fictícias (`tests/fixtures/`) e comparam as saídas com as referências em `tests/fixtures/esperado/`. Quando uma mudança de comportamento for intencional, regrave as referências com `uv run pytest --atualizar-esperado` e revise o diff antes do commit.

## Estrutura

```
main.py                     entrada do Streamlit: registra as páginas
src/dmed/
├── backend/                regras de negócio e acesso a dados
│   ├── config.py           caminhos, constantes da declaração, IDs do Drive
│   ├── fontes.py           Google Drive, planilhas e caches em CSV
│   ├── formatacao.py       CPF, nomes e valores monetários
│   ├── ocorrencias.py      inconsistências e sua severidade
│   ├── mensalidades.py     validação, família e rateio anual
│   ├── despesas.py         despesas de coparticipação
│   ├── descontos.py        descontos em folha
│   ├── consulta.py         consulta por CPF do titular
│   ├── arquivo_dmed.py     arquivo .DEC da DMED
│   └── informe_pdf.py      informe de IRPF em PDF
└── frontend/               interface Streamlit
    ├── componentes.py      menu, logo, cartões e estilos compartilhados
    ├── paginas/
    │   ├── informe_irpf.py página inicial (URL /)
    │   └── arquivo_dmed.py geração do arquivo DMED (URL /DMED)
    ├── assets/             logo e favicon
    └── conteudo/
        └── manual_de_regras.md
data/                       planilhas de entrada e caches gerados
tests/                      testes e fixtures fictícias
graphify-out/               grafo de conhecimento do código (graphify)
```

Os arquivos da raiz são configurações que cada ferramenta procura ali: `pyproject.toml` e `uv.lock` (uv), `.streamlit/` (Streamlit), `.pre-commit-config.yaml` (pre-commit), `.gitignore`, `.gitattributes` e `.git-blame-ignore-revs` (git e GitHub), `.editorconfig` (editores) e `LICENSE`.

## Dados

- `data/mensalidades/MENSALIDADES.xlsx` e `data/descontos/DESCONTOS.xlsx` vêm do Google Drive. São baixados quando faltam e atualizados pelo botão **Reprocessar dados**, em *Opções avançadas* na página inicial. Não são versionados.
- `data/despesas/` e a planilha "ANTIGAS" de `data/descontos/` ainda não estão no Drive e por isso ficam no repositório.
- `data/cache/` guarda os CSVs gerados pelo processamento. Não são versionados.

## Deploy

Streamlit Community Cloud, com `main.py` como arquivo de entrada. As dependências são instaladas a partir do `uv.lock`. A senha e os IDs do Drive ficam em *App settings > Secrets*, no mesmo formato de `.streamlit/secrets.toml.example`.

## Licença

Uso exclusivo da COSEMI. Veja [LICENSE](LICENSE).

**Autor:** [Tairone Amaral](https://www.linkedin.com/in/tairone-amaral/)
