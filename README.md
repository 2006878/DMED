# DMED COSEMI

Aplicação [Streamlit](https://streamlit.io/) da COSEMI com duas páginas:

- **Informe de plano de saúde (IRPF):** consulta pelo CPF do titular e gera o PDF do informe do ano-calendário anterior.
- **Arquivo DMED:** gera o arquivo `.DEC` da DMED para a Receita Federal, com relatório das inconsistências encontradas nas planilhas. Protegida por senha.

## Requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/), que também instala o Python 3.11 definido em `.python-version`.

## Instalação

```sh
uv sync
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Preencha a senha da página DMED em `.streamlit/secrets.toml`. Esse arquivo não é versionado.

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
```

Os testes rodam sobre planilhas fictícias (`tests/fixtures/`) e comparam as saídas com as referências em `tests/fixtures/esperado/`. Quando uma mudança de comportamento for intencional, regrave as referências com `uv run pytest --atualizar-esperado` e revise o diff antes do commit.

## Estrutura

```
main.py                          entrada do Streamlit: registra as páginas
src/dmed/
├── backend/
│   └── processamento.py         planilhas, caches, arquivo DMED e PDF
└── frontend/
    ├── paginas/
    │   ├── informe_irpf.py      página inicial (URL /)
    │   └── arquivo_dmed.py      geração do arquivo DMED (URL /DMED)
    ├── assets/                  logo e favicon
    └── conteudo/
        └── manual_de_regras.md  manual exibido na página do arquivo DMED
data/                            planilhas de entrada e caches gerados
tests/                           testes e fixtures fictícias
```

Os arquivos da raiz são configurações que cada ferramenta procura ali: `pyproject.toml` e `uv.lock` (uv), `.python-version` (versão do Python), `.streamlit/` (Streamlit), `.gitignore`, `.gitattributes` e `.git-blame-ignore-revs` (git e GitHub), `.editorconfig` (editores) e `LICENSE`.

## Dados

- `data/mensalidades/` e `data/descontos/DESCONTOS.xlsx` são baixados do Google Drive pelo botão **Reprocessar dados**, em *Opções avançadas* na página inicial.
- `data/despesas/` e as demais planilhas de `data/descontos/` vêm do repositório.
- `data/cache/` guarda os CSVs gerados pelo processamento. Eles não são versionados.

## Deploy

Streamlit Community Cloud, com `main.py` como arquivo de entrada. As dependências são instaladas a partir do `uv.lock`. A senha fica em *App settings > Secrets*, no mesmo formato de `.streamlit/secrets.toml.example`.

## Licença

Uso exclusivo da COSEMI. Veja [LICENSE](LICENSE).

**Autor:** [Tairone Amaral](https://www.linkedin.com/in/tairone-amaral/)
