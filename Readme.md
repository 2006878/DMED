# 📌 Streamlit Application

Este repositório contém uma aplicação desenvolvida com [Streamlit](https://streamlit.io/). Abaixo estão as instruções para configurar o ambiente, instalar as dependências e rodar a aplicação corretamente.

---

## 🔧 Configuração do Ambiente Virtual

### Criando e ativando o ambiente virtual

Para garantir um ambiente isolado e evitar conflitos de dependências, siga os passos abaixo para criar e ativar um ambiente virtual.

### 📌 Windows (cmd/powershell):
```sh
python -m venv venv
venv\Scripts\activate
```

### 📌 macOS/Linux (bash/zsh):
```sh
python3 -m venv venv
source venv/bin/activate
```

Após a ativação, o terminal exibirá algo semelhante a `(venv)`, indicando que o ambiente virtual está ativo.

---

## 📦 Instalação das Dependências

Com o ambiente virtual ativado, instale todas as bibliotecas listadas no `requirements.txt` com o seguinte comando:

```sh
pip install -r requirements.txt
```

Para verificar se todas as dependências foram instaladas corretamente, use:

```sh
pip list
```

---

## 🚀 Executando a Aplicação Streamlit

Após a configuração do ambiente e instalação das dependências, rode a aplicação com o seguinte comando:

```sh
streamlit run main.py
```

Isso iniciará um servidor local, e o terminal exibirá um link semelhante a este:

```
  Local URL: http://localhost:8501
  Network URL: http://192.168.X.X:8501
```

Abra o link no seu navegador para acessar a aplicação.

---

## ❌ Desativando o Ambiente Virtual

Após terminar de usar a aplicação, você pode desativar o ambiente virtual com:

```sh
deactivate
```

---

## 🛠 Solução de Problemas

1. **Streamlit não encontrado?**
   - Certifique-se de que o ambiente virtual está ativado.
   - Reinstale as dependências com `pip install -r requirements.txt`.

2. **Erro de permissão em macOS/Linux?**
   - Tente `chmod +x venv/bin/activate` e execute `source venv/bin/activate` novamente.

3. **Porta 8501 já em uso?**
   - Rode o Streamlit em outra porta: `streamlit run main.py --server.port 8502`

Se o problema persistir, crie uma issue no repositório! 🚀

---

## 📜 Licença

Este projeto é distribuído sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

📝 **Autor:** [Tairone Amaral](https://www.linkedin.com/in/tairone-amaral/)

🌟 Se este projeto foi útil para você, não se esqueça de dar uma ⭐ no repositório!
