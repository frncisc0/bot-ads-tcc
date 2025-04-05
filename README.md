# bot-ads-tcc

Chatbot Educacional para estudantes de **Análise e Desenvolvimento de Sistemas (ADS)**, integrado ao **Telegram** com suporte a **Inteligência Artificial** via OpenRouter.

Este projeto faz parte do Trabalho de Conclusão de Curso (TCC) de Francisco F. Dantas.

---

##  Funcionalidades

- Cadastro inicial do usuário (nome e RA com validação)
- Armazenamento local em banco SQLite
- Integração com IA para tirar dúvidas técnicas
- Suporte a perguntas sobre:
  - Programação (Python, Java, C#, etc.)
  - Banco de dados (SQL/NoSQL)
  - Engenharia de Software
  - Redes e Segurança da Informação
- Comandos rápidos:
  - `/start`, `/sobre`, `/tcc`, `/reset`

---

##  Tecnologias Utilizadas

- Python 3.12+
- Telegram Bot API
- OpenRouter (modelo DeepSeek)
- SQLite (banco local)
- python-telegram-bot 20.x
- httpx
- dotenv

---

## 🛠 Como executar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/frncisc0/bot-ads-tcc.git
cd bot-ads-tcc

