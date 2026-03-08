import os


BASE_DIR = os.getcwd()

MENSALIDADES_FILE = "mensalidade_file.csv"
DESPESAS_FILE = "despesas_file.csv"
DESCONTOS_FILE = "descontos_file.csv"

DESPESAS_DIR = "despesas_nova"
DESCONTOS_DIR = "descontos"


def build_path(filename: str) -> str:
    return os.path.join(BASE_DIR, filename)

