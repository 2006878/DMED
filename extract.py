from funcoes import (
    busca_dados_mensalidades,
    processa_descontos,
    processa_despesas,
    processa_mensalidades,
)


def main():
    # Criar os arquivos base se não existir
    # processa_mensalidades()
    # processa_descontos()
    # processa_despesas()
    busca_dados_mensalidades("90782429653")


if __name__ == "__main__":
    main()
