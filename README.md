# 📚 Assistente ADS - Bot Educacional de Telegram para TCC

## 🎯 Visão Geral do Projeto

O **Assistente ADS** é um bot educacional desenvolvido para a plataforma Telegram, criado como um projeto de Trabalho de Conclusão de Curso (TCC) na área de Análise e Desenvolvimento de Sistemas. Seu principal objetivo é servir como uma ferramenta de apoio interativa para estudantes, oferecendo respostas técnicas e precisas sobre conceitos do curso, além de fornecer informações relevantes sobre o TCC.

Utilizando Inteligência Artificial (IA) para processar e responder às dúvidas dos usuários, o bot visa promover um aprendizado dinâmico e acessível, com um toque de bom humor e analogias para tornar a experiência mais leve.

## ✨ Funcionalidades Principais

* **Cadastro de Alunos:** Permite que novos usuários se registrem fornecendo nome e Registro Acadêmico (RA) para personalização do atendimento e controle de interações.
* **Consultas à IA:** Responde a dúvidas técnicas sobre programação, banco de dados, engenharia de software, análise de sistemas e outros tópicos relevantes para o curso de ADS, utilizando o modelo DeepSeek via OpenRouter.
* **Informações do Projeto (/sobre):** Apresenta detalhes sobre o desenvolvimento do bot, tecnologias empregadas e o desenvolvedor responsável.
* **Detalhes do TCC (/tcc):** Oferece informações sobre o Trabalho de Conclusão de Curso, incluindo prazos, orientador e links diretos para o podcast e a documentação completa do projeto.
* **Registro de Interações:** Armazena dados de uso para análise, auxiliando na avaliação e aprimoramento contínuo do bot.
* **Validação de Entradas:** Implementa validações para garantir a qualidade dos dados fornecidos pelos usuários (ex: formato de nome e RA).

## 🚀 Tecnologias Utilizadas

O Assistente ADS é construído sobre uma pilha de tecnologias modernas e robustas:

* **Python 3.x:** Linguagem de programação principal.
* **`python-telegram-bot`:** Framework para interação com a API do Telegram.
* **`python-dotenv`:** Para gerenciamento seguro de variáveis de ambiente.
* **`httpx`:** Cliente HTTP assíncrono para comunicação com a API da IA.
* **SQLite3:** Banco de dados leve para armazenamento local de informações de alunos e interações.
* **OpenRouter API:** Plataforma de agregação de APIs de IA, utilizada para acessar o modelo `deepseek/deepseek-chat`.

## ⚙️ Configuração e Instalação

Para rodar o bot localmente, siga os passos abaixo:

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/frncisc0/bot-ads-tcc.git](https://github.com/frncisc0/bot-ads-tcc.git)
    cd bot-ads-tcc
    ```

2.  **Crie um ambiente virtual (recomendado):**
    ```bash
    python -m venv .venv
    # No Windows:
    .venv\Scripts\activate
    # No macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Certifique-se de ter um arquivo `requirements.txt` com `python-telegram-bot`, `python-dotenv`, `httpx` e `sqlite3` - embora `sqlite3` seja built-in, a biblioteca do `python-telegram-bot` e `httpx` são as principais externas.)*
    Se não tiver, crie um `requirements.txt` com:
    ```
    python-telegram-bot
    python-dotenv
    httpx
    ```
    E depois rode `pip install -r requirements.txt`.

4.  **Configure as variáveis de ambiente:**
    Crie um arquivo `.env` na raiz do projeto (`bot-ads-tcc`) e adicione suas chaves de API:

    ```env
    TELEGRAM_TOKEN=SEU_TOKEN_DO_BOT_TELEGRAM
    OPENROUTER_API_KEY=SUA_CHAVE_API_OPENROUTER
    DB_PATH=db_bot_ads.sqlite # Caminho opcional para o banco de dados SQLite
    ```
    * **`TELEGRAM_TOKEN`**: Obtenha este token com o @BotFather no Telegram.
    * **`OPENROUTER_API_KEY`**: Crie uma conta no OpenRouter e gere sua chave API.

5.  **Execute o bot:**
    ```bash
    python bot_ads.py
    ```
    O bot irá inicializar o banco de dados SQLite (se não existir) e começar a escutar por mensagens no Telegram.

## 🤖 Como Usar o Bot (para o Usuário Final)

Uma vez que o bot esteja online, você pode interagir com ele no Telegram:

* **/start**: Inicia o bot e o processo de cadastro, se você for um novo usuário.
* **/sobre**: Receba informações sobre o projeto do Assistente ADS.
* **/tcc**: Acesse detalhes sobre o Trabalho de Conclusão de Curso, incluindo links para o podcast e a documentação.
* **Qualquer outra pergunta**: Digite sua dúvida sobre temas de TI (programação, banco de dados, etc.) e o bot tentará respondê-la usando inteligência artificial.

## 📈 Status do Projeto e Entrega

Este projeto está em fase de desenvolvimento como parte do TCC.
* **Desenvolvedor:** Francisco F. Dantas
* **Orientador:** Professor Nilton Mattos
* **Previsão de Entrega do TCC:** Junho/2025

### 🔗 Links Importantes

* **🎧 Podcast do Projeto:** [Baixe e Ouça o Podcast Completo Aqui!](https://drive.google.com/file/d/16XpXbCgUhRczxrZ-N8y5TVA7JfBqb1uo/view?usp=drive_link)
* **📄 Documentação Completa do TCC:** [Baixe a Documentação do TCC Aqui!](https://drive.google.com/file/d/1moPhStmyRY7vRt5POkkZZ-fWdnkoamX7/view?usp=drive_link)

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---