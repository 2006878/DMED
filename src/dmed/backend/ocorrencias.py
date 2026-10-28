"""Inconsistências encontradas nas planilhas, com a severidade de cada uma."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severidade(Enum):
    """O valor é o ícone que abre a mensagem no relatório de inconsistências."""

    ALERTA = "⚠️"  # problema de estrutura ou de dado opcional
    AVISO = "🟡"  # CPF ausente: o sistema tenta mapear pelo nome
    ERRO = "🛑"  # dado obrigatório em branco
    CRITICO = "❌"  # falha que impede processar uma planilha

    @property
    def bloqueante(self) -> bool:
        """Se o arquivo DMED precisa de correção antes de ir para a Receita."""
        return self in (Severidade.ERRO, Severidade.CRITICO)


@dataclass(frozen=True)
class Ocorrencia:
    severidade: Severidade
    texto: str

    def __str__(self) -> str:
        return f"{self.severidade.value} {self.texto}"


def alerta(texto: str) -> Ocorrencia:
    return Ocorrencia(Severidade.ALERTA, texto)


def aviso(texto: str) -> Ocorrencia:
    return Ocorrencia(Severidade.AVISO, texto)


def erro(texto: str) -> Ocorrencia:
    return Ocorrencia(Severidade.ERRO, texto)


def critico(texto: str) -> Ocorrencia:
    return Ocorrencia(Severidade.CRITICO, texto)
