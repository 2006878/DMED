"""Consulta por CPF do titular: mensalidades, descontos e despesas.

As bases processadas são lidas uma vez por versão do CSV e indexadas por CPF.
Cada consulta aplica ao subconjunto do titular exatamente as mesmas operações
de antes, para que os valores não mudem em nenhum centavo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from dmed.backend import descontos, despesas, fontes, mensalidades
from dmed.backend.formatacao import formatar_cpf, formatar_moeda, ler_valor_monetario
from dmed.backend.ocorrencias import Ocorrencia

Processador = Callable[[], tuple[Path | None, list[Ocorrencia]]]

# Ordem em que os caches são gerados quando faltam (despesas usa mensalidades).
ETAPAS: tuple[tuple[str, Processador], ...] = (
    (mensalidades.CACHE, mensalidades.processar_mensalidades),
    (descontos.CACHE, descontos.processar_descontos),
    (despesas.CACHE, despesas.processar_despesas),
)


class MensalidadesIndisponiveis(RuntimeError):
    """O cache de mensalidades está vazio: não há o que consultar."""

    def __init__(self) -> None:
        super().__init__("Erro ao processar mensalidades — verifique o arquivo do Google Drive")


def _agrupar(df: pd.DataFrame, coluna: str) -> dict[str, pd.DataFrame]:
    return {str(chave): grupo for chave, grupo in df.groupby(coluna, sort=False)}


def _somar(df: pd.DataFrame, chave: str, valor: str) -> dict[str, float]:
    # Series.sum() em cada subconjunto, como a consulta original fazia.
    return {
        str(nome): float(grupo[valor].sum()) for nome, grupo in df.groupby(chave, sort=False)
    }


@dataclass(frozen=True)
class BaseMensalidades:
    vazia: bool
    por_titular: dict[str, pd.DataFrame]
    modelo: pd.DataFrame  # sem linhas: o resultado para um CPF sem cadastro


@dataclass(frozen=True)
class BaseDescontos:
    tem_cpf: bool
    por_cpf: dict[str, float]
    por_nome: dict[str, float]


@dataclass(frozen=True)
class BaseDespesas:
    vazia: bool
    por_cpf: dict[str, pd.DataFrame]


@lru_cache(maxsize=2)
def _base_mensalidades(versao: tuple[str, int, int]) -> BaseMensalidades:
    df = fontes.ler_cache(mensalidades.CACHE, como_texto=True)
    if df.empty:
        return BaseMensalidades(vazia=True, por_titular={}, modelo=df)
    df["Titular_CPF"] = df["Titular_CPF"].map(formatar_cpf)
    return BaseMensalidades(vazia=False, por_titular=_agrupar(df, "Titular_CPF"), modelo=df.iloc[0:0])


@lru_cache(maxsize=2)
def _base_descontos(versao: tuple[str, int, int]) -> BaseDescontos | None:
    df = fontes.ler_cache(descontos.CACHE, como_texto=False)
    if df.empty:
        return None
    if "Total de Descontos" not in df.columns and "Valor a Pagar" in df.columns:
        df["Total de Descontos"] = df["Valor a Pagar"]
    if "Total de Descontos" not in df.columns or "Nome" not in df.columns:
        return None
    tem_cpf = "CPF" in df.columns
    if tem_cpf:
        df["CPF"] = df["CPF"].map(formatar_cpf)
    df["Nome"] = df["Nome"].astype(str).str.strip().str.upper()
    df["Total de Descontos"] = df["Total de Descontos"].map(ler_valor_monetario)
    return BaseDescontos(
        tem_cpf=tem_cpf,
        por_cpf=_somar(df, "CPF", "Total de Descontos") if tem_cpf else {},
        por_nome=_somar(df, "Nome", "Total de Descontos"),
    )


@lru_cache(maxsize=2)
def _base_despesas(versao: tuple[str, int, int]) -> BaseDespesas:
    df = fontes.ler_cache(despesas.CACHE, como_texto=False)
    if df.empty:
        return BaseDespesas(vazia=True, por_cpf={})
    df["CPF_DO_RESPONSAVEL"] = df["CPF_DO_RESPONSAVEL"].map(formatar_cpf)
    return BaseDespesas(vazia=False, por_cpf=_agrupar(df, "CPF_DO_RESPONSAVEL"))


def _versao(cache: str) -> tuple[str, int, int]:
    versao = fontes.assinatura(fontes.caminho_cache(cache))
    if versao is None:
        raise fontes.CacheIndisponivel(cache)
    return versao


@dataclass(frozen=True)
class Consulta:
    """Bases carregadas; `None` quando o cache não existe ou não pôde ser lido."""

    base_mensalidades: BaseMensalidades | None
    base_descontos: BaseDescontos | None
    base_despesas: BaseDespesas | None
    _nomes: dict[str, str] = field(default_factory=dict, compare=False)

    @classmethod
    def carregar(cls, *, ignorar: frozenset[str] = frozenset()) -> Consulta:
        """Gera os caches que faltam e carrega as bases.

        `ignorar` lista caches cujo processamento acabou de falhar: o arquivo
        antigo no disco não deve ser usado no lugar deles.
        """
        with fontes.TRAVA:
            for cache, processar in ETAPAS:
                if cache not in ignorar and not fontes.cache_existe(cache):
                    processar()
            return cls(
                base_mensalidades=_carregar(mensalidades.CACHE, _base_mensalidades, ignorar),
                base_descontos=_carregar_descontos(ignorar),
                base_despesas=_carregar(despesas.CACHE, _base_despesas, ignorar),
            )

    def mensalidades(self, cpf: str) -> pd.DataFrame:
        """Valor anual de cada membro da família, titular primeiro."""
        base = self.base_mensalidades
        if base is None:
            return pd.DataFrame()
        if base.vazia:
            raise MensalidadesIndisponiveis
        df = base.por_titular.get(cpf, base.modelo).copy()
        df["Total"] = pd.to_numeric(
            df["Total"].astype(str).str.replace(",", "."), errors="coerce"
        ).fillna(0)
        df["Ordem"] = (df["Relação"] != "Titular").astype(int)
        df = df.groupby(["Nome", "Ordem"], as_index=False).agg({"Total": "sum"})
        df["Total"] = pd.to_numeric(df["Total"], errors="coerce").round(2)
        df = df.sort_values(by=["Ordem", "Total"], ascending=[True, False])
        df = df[["Nome", "Total"]].rename(columns={"Total": "Valor"})
        df["Valor"] = df["Valor"].map(formatar_moeda)
        return df

    def descontos(self, cpf: str) -> float:
        """Total descontado em folha: pelo CPF ou, sem CPF, pelo nome do titular."""
        if self.base_mensalidades is not None and self.base_mensalidades.vazia:
            raise MensalidadesIndisponiveis
        base = self.base_descontos
        if base is None:
            return 0.0
        cpf_formatado = formatar_cpf(cpf)
        if cpf_formatado and base.tem_cpf and cpf_formatado in base.por_cpf:
            return base.por_cpf[cpf_formatado]
        total = 0.0
        nome = self._nome_do_titular(cpf)
        if nome and nome in base.por_nome:
            total += base.por_nome[nome]
        return total

    def despesas(self, cpf: str, nome: str) -> pd.DataFrame:
        """Despesas de coparticipação da família, ajustadas ao total descontado."""
        base = self.base_despesas
        if base is None:
            return pd.DataFrame()
        valor_descontos = float(self.descontos(cpf))
        if not base.vazia and cpf in base.por_cpf:
            tabela = _ajustar_ao_desconto(base.por_cpf[cpf].copy(), nome, valor_descontos)
        else:
            tabela = pd.DataFrame({"BENEFICIARIO": [nome], "VALOR_DO_SERVICO": [valor_descontos]})
        tabela["VALOR_DO_SERVICO"] = tabela["VALOR_DO_SERVICO"].map(formatar_moeda)
        return tabela[["BENEFICIARIO", "VALOR_DO_SERVICO"]].rename(
            columns={"BENEFICIARIO": "Nome", "VALOR_DO_SERVICO": "Valor"}
        )

    def tem_despesas(self, cpf: str) -> bool:
        base = self.base_despesas
        return base is not None and cpf in base.por_cpf

    def _nome_do_titular(self, cpf: str) -> str:
        if cpf not in self._nomes:
            familia = self.mensalidades(cpf)
            self._nomes[cpf] = (
                str(familia["Nome"].iloc[0]).strip().upper() if not familia.empty else ""
            )
        return self._nomes[cpf]


def _carregar(
    cache: str,
    construir: Callable[[tuple[str, int, int]], BaseMensalidades | BaseDespesas],
    ignorar: frozenset[str],
) -> Any:
    if cache in ignorar:
        return None
    try:
        return construir(_versao(cache))
    except fontes.CacheIndisponivel:
        return None


def _carregar_descontos(ignorar: frozenset[str]) -> BaseDescontos | None:
    if descontos.CACHE in ignorar:
        return None
    try:
        return _base_descontos(_versao(descontos.CACHE))
    except fontes.CacheIndisponivel:
        return None


def _ajustar_ao_desconto(tabela: pd.DataFrame, nome: str, valor_descontos: float) -> pd.DataFrame:
    """Faz as despesas da família somarem o total descontado em folha.

    A diferença é distribuída igualmente entre os dependentes (as linhas que
    não são do titular); quem não tem saldo suficiente fica zerado e a sobra é
    redistribuída. Valores negativos que restarem são abatidos do primeiro
    positivo. Uma família com uma só linha recebe o valor do desconto.
    """
    diferenca = valor_descontos - tabela["VALOR_DO_SERVICO"].sum()
    tabela["BENEFICIARIO"] = tabela["BENEFICIARIO"].str.strip().str.upper()
    do_titular = tabela["BENEFICIARIO"] == nome.strip().upper()
    if do_titular.any():
        tabela["ordem"] = do_titular
        tabela = tabela.sort_values("ordem", ascending=False).drop("ordem", axis=1)

    restantes = ~do_titular
    qtd_restantes = restantes.sum()
    total_restantes = tabela.loc[restantes, "VALOR_DO_SERVICO"].sum()

    if diferenca != 0:
        if qtd_restantes > 0 and (total_restantes >= abs(diferenca) or diferenca > 0):
            por_registro = abs(diferenca) / qtd_restantes
            insuficientes = pd.Series(False, index=tabela.index)
            if diferenca < 0:
                insuficientes = restantes & (tabela["VALOR_DO_SERVICO"] < por_registro)
            if insuficientes.any():
                sem_saldo = tabela.loc[insuficientes, "VALOR_DO_SERVICO"]
                tabela.loc[insuficientes, "VALOR_DO_SERVICO"] = 0
                diferenca += sem_saldo.sum()
                restantes = restantes & ~insuficientes
                qtd_restantes = restantes.sum()
                if qtd_restantes > 0:
                    por_registro = abs(diferenca) / qtd_restantes
            if qtd_restantes > 0:
                if diferenca < 0:
                    tabela.loc[restantes, "VALOR_DO_SERVICO"] -= por_registro
                else:
                    tabela.loc[restantes, "VALOR_DO_SERVICO"] += por_registro

        if qtd_restantes > 0 and total_restantes < abs(diferenca) and diferenca < 0:
            tabela.loc[restantes, "VALOR_DO_SERVICO"] = 0
            tabela.at[tabela.index[0], "VALOR_DO_SERVICO"] = valor_descontos
        elif len(tabela) == 1:
            tabela.at[tabela.index[0], "VALOR_DO_SERVICO"] = valor_descontos

    negativos = tabela["VALOR_DO_SERVICO"] < 0
    total_negativos = tabela.loc[negativos, "VALOR_DO_SERVICO"].sum()
    if total_negativos < 0:
        primeiro_positivo = tabela[tabela["VALOR_DO_SERVICO"] > 0].index.min()
        if pd.notna(primeiro_positivo):
            tabela.at[primeiro_positivo, "VALOR_DO_SERVICO"] += total_negativos
        tabela.loc[negativos, "VALOR_DO_SERVICO"] = 0
    return tabela
