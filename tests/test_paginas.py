"""Smoke tests das páginas com streamlit.testing.v1.AppTest, rodando sobre as
planilhas fictícias do fixture `ambiente`."""

from collections.abc import Callable

import pytest
from conftest import RAIZ
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Button, TextInput

Esperado = Callable[[str, str], None]

ENTRADA = RAIZ / "main.py"
PAGINA_DMED = "pages/2_DMED.py"
SENHA = "senha-de-teste"
pytestmark = pytest.mark.usefixtures("ambiente")


def abre_inicio() -> AppTest:
    return AppTest.from_file(str(ENTRADA), default_timeout=60).run()


def abre_dmed_autenticado() -> AppTest:
    at = abre_inicio()
    at.secrets["password"] = SENHA
    at.switch_page(PAGINA_DMED).run()
    at.text_input(key="password").input(SENHA).run()
    return at


def botao(at: AppTest, rotulo: str) -> Button:
    return next(b for b in at.button if b.label == rotulo)


def campo(at: AppTest, inicio_do_rotulo: str) -> TextInput:
    return next(t for t in at.text_input if t.label.startswith(inicio_do_rotulo))


def test_inicio_sem_cpf() -> None:
    at = abre_inicio()

    assert not at.exception
    assert [t.value for t in at.sidebar.title] == ["Menu COSEMI"]
    assert [t.value for t in at.main.title] == [
        "INFORME PLANO DE SAÚDE 2025 IRPF - COSEMI"
    ]
    assert not at.download_button


def test_inicio_consulta_cpf(esperado: Esperado) -> None:
    at = abre_inicio()
    at.text_input(key="cpf_input").input("100.000.000-01").run()

    assert not at.exception
    cartoes = [
        m.value.strip()
        for m in at.markdown
        if "<div class='info-container'>" in m.value
    ]
    esperado("tela_inicio_10000000001.txt", "\n\n".join(cartoes) + "\n")
    assert [b.label for b in at.download_button] == ["📥 Download PDF"]


def test_inicio_cpf_sem_registros() -> None:
    at = abre_inicio()
    at.text_input(key="cpf_input").input("99999999999").run()

    assert not at.exception
    assert [i.value for i in at.info] == [
        "Não existem registros de mensalidades para o CPF informado.",
        "Não existem registros de descontos para o CPF informado.",
    ]


def test_menu_lateral_navega_entre_paginas() -> None:
    at = abre_inicio()
    botao(at, "⚙️ DMED").click().run()

    assert not at.exception
    assert [t.label for t in at.text_input] == ["Senha"]

    at.secrets["password"] = SENHA
    at.text_input(key="password").input(SENHA).run()
    botao(at, "🏠 Home").click().run()

    assert [t.value for t in at.main.title] == [
        "INFORME PLANO DE SAÚDE 2025 IRPF - COSEMI"
    ]


def test_dmed_senha_incorreta() -> None:
    at = abre_inicio()
    at.secrets["password"] = SENHA
    at.switch_page(PAGINA_DMED).run()
    at.text_input(key="password").input("errada").run()

    assert not at.exception
    assert [(e.icon, e.value) for e in at.error] == [("😕", "Senha incorreta")]
    assert not at.main.title


def test_dmed_exibe_formulario_e_manual() -> None:
    at = abre_dmed_autenticado()

    assert not at.exception
    assert [t.value for t in at.main.title] == ["DOWNLOAD ARQUIVO DMED - COSEMI"]
    manual = (RAIZ / "docs" / "manual.md").read_text(encoding="utf-8")
    assert any(m.value == manual.strip() for m in at.markdown)


def test_dmed_gera_arquivo_com_relatorio_de_erros() -> None:
    at = abre_dmed_autenticado()
    campo(at, "Digite o CPF do Responsável").input("00000000191")
    campo(at, "Digite o nome do Responsável").input("RESPONSAVEL TESTE")
    campo(at, "Digite o DDD").input("31")
    campo(at, "Digite o telefone").input("999999999")
    at.run()
    botao(at, "📥 Processar e criar arquivo DMED").click().run()

    assert not at.exception
    assert at.warning[0].icon == "⚠️"
    assert at.warning[0].value.startswith("**ATENÇÃO:** O arquivo DMED foi gerado")
    assert [b.label for b in at.download_button] == [
        "📥 BAIXAR RELATÓRIO DE ERROS (.txt)",
        "📥 BAIXAR DMED (COM ERROS) (.DEC)",
    ]
