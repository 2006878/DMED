"""Resultado da geração do arquivo DMED, guardado na sessão entre os downloads.

Fica fora da página porque o Streamlit reexecuta a página a cada clique: uma
classe definida lá seria recriada, e o resultado guardado deixaria de ser
reconhecido.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from dmed.backend import config
from dmed.backend.ocorrencias import Ocorrencia


@dataclass(frozen=True)
class ResultadoDmed:
    conteudo: str | None
    ocorrencias: list[Ocorrencia] = field(default_factory=list)
    gerado_em: datetime = field(default_factory=config.agora)
    falha: str = ""

    @property
    def bloqueantes(self) -> list[Ocorrencia]:
        return [o for o in self.ocorrencias if o.severidade.bloqueante]

    def contar(self, registro: str) -> int:
        """Quantas linhas do arquivo são do tipo de registro (TOP, DTOP...)."""
        linhas = (self.conteudo or "").splitlines()
        return sum(linha.startswith(f"{registro}|") for linha in linhas)

    def relatorio_de_erros(self) -> str:
        separador = "========================================================\n"
        return (
            separador
            + "RELATORIO DE INCONSISTENCIAS - COSEMI DMED\n"
            + f"Gerado em: {self.gerado_em:%d/%m/%Y as %H:%M:%S}\n"
            + separador
            + "\n"
            + "Por favor, corrija as linhas listadas abaixo nas planilhas originais:\n\n"
            + "\n".join(str(o) for o in self.ocorrencias)
        )
