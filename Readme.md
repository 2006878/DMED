
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



### Opção 2: Usando Docker

Se você preferir usar Docker, siga estas instruções para criar e executar um container com a aplicação.

#### Pré-requisitos
- Docker instalado em seu sistema ([Instruções de instalação](https://docs.docker.com/get-docker/))

#### 🐳 Construindo a imagem Docker

1. Navegue até o diretório raiz do projeto (onde está o arquivo `Dockerfile`)
2. Execute o comando para construir a imagem:

```sh
docker build -t cosemi .
```


#### 🚀 Executando o container


Após a construção da imagem, execute o container com:


```sh
docker run -p 8501:8501 --name cosemi-container cosemi
```


Para executar o container em segundo plano (modo detached):

```sh

docker run -d -p 8501:8501 --name cosemi-container cosemi
```

#### 🌐 Acessando a aplicação

Abra seu navegador e acesse:
```
http://localhost:8501
```

#### ⚙️ Gerenciando o container

Para parar o container:
```sh
docker stop cosemi-container
```

Para iniciar um container que foi parado:
```sh
docker start cosemi-container
```

Para remover o container:
```sh
docker rm cosemi-container
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
   - Ou, se estiver usando Docker: `docker run -p 8502:8501 --name cosemi-container cosemi`

4. **Não consegue acessar a aplicação no Docker?**
   - Certifique-se de acessar `http://localhost:8501` (não `0.0.0.0:8501`)
   - Verifique se o container está rodando com `docker ps`
   - Verifique os logs com `docker logs cosemi-container`

Se o problema persistir, crie uma issue no repositório! 🚀

---

## 📜 Licença

Este projeto é distribuído sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

📝 **Autor:** [Tairone Amaral](https://www.linkedin.com/in/tairone-amaral/)

🌟 Se este projeto foi útil para você, não se esqueça de dar uma ⭐ no repositório!
