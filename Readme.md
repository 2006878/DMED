
# 📌 Streamlit Application - COSEMI


Este repositório contém uma aplicação desenvolvida com [Streamlit](https://streamlit.io/) para o sistema DMED da COSEMI. Abaixo estão as instruções para configurar o ambiente, instalar as dependências e rodar a aplicação corretamente.

---


## 🔧 Configuração do Ambiente


Você pode executar esta aplicação de duas maneiras: usando um ambiente virtual Python ou usando Docker.

### Opção 1: Ambiente Virtual Python

#### Criando e ativando o ambiente virtual

Para garantir um ambiente isolado e evitar conflitos de dependências, siga os passos abaixo para criar e ativar um ambiente virtual.


##### 📌 Windows (cmd/powershell):
```sh
python -m venv venv
venv\Scripts\activate
```


##### 📌 macOS/Linux (bash/zsh):
```sh
python3 -m venv venv
source venv/bin/activate
```

Após a ativação, o terminal exibirá algo semelhante a `(venv)`, indicando que o ambiente virtual está ativo.


#### 📦 Instalação das Dependências



Com o ambiente virtual ativado, instale todas as bibliotecas listadas no `requirements.txt` com o seguinte comando:

```sh
pip install -r requirements.txt
```

Para verificar se todas as dependências foram instaladas corretamente, use:

```sh
pip list
```


#### 🚀 Executando a Aplicação Streamlit



Após a configuração do ambiente e instalação das dependências, rode a aplicação com o seguinte comando:

```sh
streamlit run main.py
```


#### ❌ Desativando o Ambiente Virtual

Após terminar de usar a aplicação, você pode desativar o ambiente virtual com:

```sh
deactivate
```



### Opção 2: Usando Docker Compose

Se você preferir usar Docker Compose, siga estas instruções para criar e executar os serviços da aplicação.

#### Pré-requisitos
- Docker e Docker Compose instalados em seu sistema ([Instruções de instalação](https://docs.docker.com/get-docker/))

#### 🐳 Criando o arquivo `docker-compose.yml`

Certifique-se de que o arquivo `docker-compose.yml` esteja no diretório raiz do projeto com o seguinte conteúdo:

```yaml
version: '3'
services:
  app:
    image: cosemi
    container_name: cosemi-container
    ports:
      - "8501:8501"
    volumes:
      - .:/app
    environment:
      - STREAMLIT_SERVER_RUN_ON_SAVE=true
      - WATCHDOG_TIMEOUT=10
```

#### 🚀 Executando os serviços

1. Navegue até o diretório raiz do projeto (onde está o arquivo `docker-compose.yml`).
2. Execute o seguinte comando para iniciar os serviços:

```sh
docker-compose up
```

Para executar os serviços em segundo plano (modo detached):

```sh
docker-compose up -d
```

#### 🌐 Acessando a aplicação

Abra seu navegador e acesse:
```
http://localhost:8501
```

#### ⚙️ Gerenciando os serviços

Para parar os serviços:
```sh
docker-compose down
```

Para reiniciar os serviços:
```sh
docker-compose restart
```

Para visualizar os logs:
```sh
docker-compose logs
```

---

## 🛠 Solução de Problemas

1. **Porta 8501 já em uso?**
   - Altere a porta no arquivo `docker-compose.yml`:
     ```yaml
     ports:
       - "8502:8501"
     ```
   - Em seguida, acesse a aplicação em `http://localhost:8502`.

2. **Erro ao construir a imagem?**
   - Certifique-se de que o arquivo `Dockerfile` está no diretório correto e que não há erros de sintaxe.

3. **Não consegue acessar a aplicação?**
   - Verifique se os serviços estão rodando com `docker-compose ps`.
   - Verifique os logs com `docker-compose logs`.

Se o problema persistir, crie uma issue no repositório! 🚀

---

## 📜 Licença

Este projeto é distribuído sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

📝 **Autor:** [Tairone Amaral](https://www.linkedin.com/in/tairone-amaral/)

🌟 Se este projeto foi útil para você, não se esqueça de dar uma ⭐ no repositório!
