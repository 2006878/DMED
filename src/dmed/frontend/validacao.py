"""Validação do que a pessoa digita nos formulários, com mensagens para a tela.

Funções puras, sem Streamlit: as páginas mostram as mensagens e os testes
conferem as regras.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from dmed.backend.arquivo_dmed import Responsavel
from dmed.backend.formatacao import formatar_cpf

DIGITOS_CPF = 11
DIGITOS_DDD = 2
DIGITOS_TELEFONE = (8, 9)


def somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def cpf_com_mascara(cpf: str) -> str:
    """'00000000191' -> '000.000.001-91'."""
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


@dataclass(frozen=True)
class CpfConsultado:
    """CPF pronto para a consulta, ou o motivo de não consultar."""

    cpf: str = ""
    aviso: str = ""
    erro: str = ""


def ler_cpf_da_consulta(digitado: str) -> CpfConsultado:
    """Aceita o CPF com ou sem máscara.

    Com menos de 11 números, completa com zeros à esquerda (como a consulta
    sempre fez, para CPFs que começam com zero) e avisa qual CPF foi usado.
    """
    digitos = somente_digitos(digitado)
    if not digitos:
        return CpfConsultado(erro="Digite os números do CPF do titular.")
    if len(digitos) > DIGITOS_CPF:
        return CpfConsultado(
            erro=f"O CPF tem {len(digitos)} números, mas deve ter 11. "
            "Confira o número digitado."
        )
    cpf = formatar_cpf(digitado)
    if len(digitos) < DIGITOS_CPF:
        return CpfConsultado(
            cpf=cpf,
            aviso=f"O CPF digitado tem {len(digitos)} números. Consultamos "
            f"{cpf_com_mascara(cpf)}, completando com zeros à esquerda. "
            "Se não for esse, corrija e consulte de novo.",
        )
    return CpfConsultado(cpf=cpf)


def validar_responsavel(
    cpf: str, nome: str, ddd: str, telefone: str
) -> tuple[Responsavel | None, list[str]]:
    """Confere os dados do responsável e devolve o que precisa ser corrigido."""
    problemas = []
    cpf_digitos = somente_digitos(cpf)
    ddd_digitos = somente_digitos(ddd)
    telefone_digitos = somente_digitos(telefone)

    if len(cpf_digitos) != DIGITOS_CPF:
        problemas.append("**CPF:** informe os 11 números.")
    if not nome.strip():
        problemas.append("**Nome completo:** campo obrigatório.")
    if len(ddd_digitos) != DIGITOS_DDD:
        problemas.append("**DDD:** informe os 2 números.")
    if len(telefone_digitos) not in DIGITOS_TELEFONE:
        problemas.append("**Telefone:** informe 8 ou 9 números, sem o DDD.")

    if problemas:
        return None, problemas
    return Responsavel(cpf_digitos, nome.strip(), ddd_digitos, telefone_digitos), []
