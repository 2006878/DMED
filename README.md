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

Com Docker:

```sh
docker compose up --build
```

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
main.py              página inicial (entrada do Streamlit)
pages/2_DMED.py      página de geração do arquivo DMED
dmed/                regras de negócio
assets/              logo e favicon
docs/manual.md       manual de regras exibido na página DMED
data/                planilhas de entrada e caches gerados
tests/               testes e fixtures fictícias
```

## Dados

- `data/mensalidades/` e `data/descontos/DESCONTOS.xlsx` são baixados do Google Drive pelo botão **Reprocessar dados**, em *Opções avançadas* na página inicial.
- `data/despesas/` e as demais planilhas de `data/descontos/` vêm do repositório.
- `data/cache/` guarda os CSVs gerados pelo processamento. Eles não são versionados.

## Deploy

Streamlit Community Cloud, com `main.py` como arquivo de entrada. As dependências são instaladas a partir do `uv.lock`. A senha fica em *App settings > Secrets*, no mesmo formato de `.streamlit/secrets.toml.example`.

## Licença

Uso exclusivo da COSEMI. Veja [LICENSE](LICENSE).

**Autor:** [Tairone Amaral](https://www.linkedin.com/in/tairone-amaral/)
