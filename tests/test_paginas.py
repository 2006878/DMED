"""Smoke tests das páginas com streamlit.testing.v1.AppTest, rodando sobre as
planilhas fictícias do fixture `ambiente`."""

from collections.abc import Callable

import pytest
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Button

from conftest import RAIZ
from dmed.backend import fontes
from dmed.frontend.componentes import ESTILO, Chaves

Esperado = Callable[[str, str], None]

ENTRADA = RAIZ / "main.py"
PAGINA_DMED = "src/dmed/frontend/paginas/arquivo_dmed.py"
SENHA = "senha-de-teste"
TITULO_INICIO = "Informe de plano de saúde"
pytestmark = pytest.mark.usefixtures("ambiente")


def abre_inicio() -> AppTest:
    return AppTest.from_file(str(ENTRADA), default_timeout=60).run()


def botao(at: AppTest, rotulo: str) -> Button:
    botoes: list[Button] = [*at.button, *at.form_submit_button]
    return next(b for b in botoes if b.label == rotulo)


def consulta(cpf: str) -> AppTest:
    at = abre_inicio()
    at.text_input(key=Chaves.CPF_CONSULTA).input(cpf)
    botao(at, "Consultar").click().run()
    assert not at.exception
    return at


def abre_dmed(senha: str | None = SENHA) -> AppTest:
    at = abre_inicio()
    if senha is not None:
        at.secrets["password"] = senha
    at.switch_page(PAGINA_DMED).run()
    return at


def entra(at: AppTest, senha: str) -> AppTest:
    at.text_input(key=Chaves.SENHA).input(senha)
    botao(at, "Entrar").click().run()
    return at


def abre_dmed_autenticado() -> AppTest:
    return entra(abre_dmed(), SENHA)


def preenche_responsavel(
    at: AppTest,
    cpf: str = "000.000.001-91",
    nome: str = "RESPONSAVEL TESTE",
    ddd: str = "31",
    telefone: str = "99999-9999",
) -> AppTest:
    at.text_input(key="dmed_cpf").input(cpf)
    at.text_input(key="dmed_nome").input(nome)
    at.text_input(key="dmed_ddd").input(ddd)
    at.text_input(key="dmed_telefone").input(telefone)
    botao(at, "Gerar arquivo DMED").click().run()
    return at


def rotulos_de_download(at: AppTest) -> list[str]:
    return [b.proto.label for b in at.get("download_button")]


# Informe IRPF -------------------------------------------------------------


def test_inicio_sem_cpf_mostra_so_a_consulta() -> None:
    at = abre_inicio()

    assert not at.exception
    assert [t.value for t in at.title] == [TITULO_INICIO]
    assert [t.label for t in at.text_input] == ["CPF do titular"]
    assert [t.placeholder for t in at.text_input] == ["000.000.000-00"]
    assert not at.metric
    assert not at.get("download_button")


def test_css_carrega_inteiro() -> None:
    # O Streamlit descarta o <style> inteiro se o CSS tiver algo parecido com
    # uma tag HTML (até num comentário).
    assert "<" not in ESTILO.read_text(encoding="utf-8")


def test_inicio_consulta_cpf(esperado: Esperado) -> None:
    at = consulta("100.000.000-01")

    tela = [at.subheader[0].value, at.caption[0].value]
    tela += [f"{m.label}: {m.value}" for m in at.metric]
    for titulo, tabela in zip(at.subheader[1:], at.table, strict=True):
        tela.append(f"\n{titulo.value}")
        tela += [" | ".join(linha) for linha in tabela.value.to_numpy().tolist()]
    esperado("tela_inicio_10000000001.txt", "\n".join(tela) + "\n")
    assert rotulos_de_download(at) == ["Baixar informe em PDF"]
    assert all(b.proto.ignore_rerun for b in at.get("download_button"))
    assert not at.warning


def test_inicio_cpf_sem_registros() -> None:
    at = consulta("99999999999")

    assert [w.value for w in at.warning] == [
        "Nenhum registro em 2025 para o CPF 999.999.999-99. Confira o número digitado."
    ]
    assert not at.metric
    assert not at.get("download_button")


def test_inicio_cpf_incompleto_avisa_o_cpf_consultado() -> None:
    at = consulta("123")

    assert at.warning[0].value.startswith(
        "O CPF digitado tem 3 números. Consultamos 000.000.001-23"
    )


def test_inicio_cpf_longo_mostra_erro_sem_consultar() -> None:
    at = consulta("1234567890123")

    assert [e.value for e in at.error] == [
        "O CPF tem 13 números, mas deve ter 11. Confira o número digitado."
    ]
    assert not at.metric


# Arquivo DMED: acesso -------------------------------------------------------


def test_dmed_pede_senha_e_explica_a_area() -> None:
    at = abre_dmed()

    assert not at.exception
    assert [t.value for t in at.title] == ["Arquivo DMED"]
    assert [t.label for t in at.text_input] == ["Senha"]
    assert not at.metric


def test_dmed_senha_incorreta() -> None:
    at = entra(abre_dmed(), "errada")

    assert not at.exception
    assert [e.value for e in at.error] == ["Senha incorreta. Tente de novo."]
    assert [t.label for t in at.text_input] == ["Senha"]


def test_dmed_sem_senha_configurada() -> None:
    at = entra(abre_dmed(senha=None), "qualquer")

    assert not at.exception
    assert [e.value for e in at.error] == [
        "A senha desta página ainda não foi configurada. Peça ao responsável "
        "técnico para cadastrá-la nos secrets do app."
    ]


def test_dmed_senha_correta_abre_o_formulario_e_a_atualizacao() -> None:
    at = abre_dmed_autenticado()

    assert not at.exception
    assert Chaves.SENHA not in at.session_state  # a senha não fica na sessão
    assert [t.label for t in at.text_input] == [
        "CPF",
        "Nome completo",
        "DDD",
        "Telefone",
    ]
    assert [s.value for s in at.subheader] == [
        "Responsável pelo preenchimento",
        "Atualizar planilhas",
    ]
    assert botao(at, "Sair")


def test_dmed_sair_volta_para_a_senha() -> None:
    at = abre_dmed_autenticado()
    botao(at, "Sair").click().run()

    assert [t.label for t in at.text_input] == ["Senha"]
    assert not at.error


# Arquivo DMED: geração --------------------------------------------------------


def test_dmed_campos_vazios_listam_o_que_falta() -> None:
    at = preenche_responsavel(abre_dmed_autenticado(), "123", "  ", "3", "1234")

    assert not at.exception
    assert at.error[0].value == (
        "Confira os campos antes de gerar o arquivo:\n\n"
        "- **CPF:** informe os 11 números.\n"
        "- **Nome completo:** campo obrigatório.\n"
        "- **DDD:** informe os 2 números.\n"
        "- **Telefone:** informe 8 ou 9 números, sem o DDD."
    )
    assert Chaves.RESULTADO_DMED not in at.session_state


def test_dmed_gera_arquivo_com_pendencias() -> None:
    at = preenche_responsavel(abre_dmed_autenticado())

    assert not at.exception
    assert at.warning[0].value.startswith(
        "Arquivo gerado com 3 pendências que impedem o envio."
    )
    assert {m.label: m.value for m in at.metric} == {
        "Titulares": "6",
        "Dependentes": "10",
        "Pendências": "3",
        "Avisos": "8",
    }
    assert rotulos_de_download(at) == [
        "Baixar DMED com pendências",
        "Baixar relatório de pendências",
    ]
    pendencias = at.dataframe[0].value
    assert list(pendencias.columns) == ["Gravidade", "Impede o envio", "Descrição"]
    assert pendencias["Impede o envio"].tolist() == ["Sim"] * 3 + ["Não"] * 8


def test_dmed_resultado_continua_depois_de_outra_interacao() -> None:
    at = preenche_responsavel(abre_dmed_autenticado())
    at.run()  # o que um download fazia antes: recarregar a página

    assert len(rotulos_de_download(at)) == 2
    botao(at, "Limpar resultado").click().run()
    assert not at.get("download_button")


def test_dmed_responsavel_vai_para_o_arquivo_sem_mascara() -> None:
    at = preenche_responsavel(abre_dmed_autenticado())

    conteudo = at.session_state[Chaves.RESULTADO_DMED].conteudo
    assert "RESPO|00000000191|RESPONSAVEL TESTE|31|999999999||||" in conteudo


# Arquivo DMED: atualização das planilhas -------------------------------------------


def test_atualizar_planilhas_sem_drive_mostra_so_o_erro() -> None:
    at = abre_dmed_autenticado()
    botao(at, "Atualizar planilhas").click().run()

    assert not at.exception
    assert at.error[0].value.startswith(
        "Não foi possível baixar as planilhas do Google Drive"
    )
    assert not at.success
    assert not at.toast


def test_atualizar_planilhas_com_sucesso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fontes, "baixar_planilhas_do_drive", lambda: (True, "ok"))
    at = abre_dmed_autenticado()
    botao(at, "Atualizar planilhas").click().run()

    assert not at.exception
    assert not at.error
    assert [t.value for t in at.toast] == ["Planilhas atualizadas."]


def test_interruptor_de_tema_no_cabecalho() -> None:
    at = abre_inicio()

    (interruptor,) = at.get("iframe")
    pagina = interruptor.proto.srcdoc
    assert 'role="switch"' in pagina
    assert 'aria-checked="false"' in pagina  # começa no claro
    assert "__" not in pagina  # todos os marcadores foram preenchidos
