import logging
import os
import sys
import httpx
import traceback
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import sqlite3
from datetime import datetime

# --- 🔹 Verificação e Instalação de Dependências ---
try:
    from dotenv import load_dotenv
except ImportError:
    import subprocess
    print(" Instalando python-dotenv...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv

# ---  Configuração Inicial ---
load_dotenv()

#  Variáveis de ambiente
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_API_KEY:
    raise ValueError(
        "Configure suas variáveis de ambiente no arquivo .env:\n"
        "TELEGRAM_TOKEN=seu_token_aqui\n"
        "OPENROUTER_API_KEY=sua_chave_aqui"
    )

# --- 🔹 Configuração da API OpenRouter ---
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = SYSTEM_PROMPT = """Você é o Assistente ADS, um chatbot educacional criado para apoiar estudantes de Análise e Desenvolvimento de Sistemas (ADS). 
Seu objetivo é fornecer respostas técnicas e precisas sobre temas relacionados ao curso, promovendo o aprendizado interativo.

🎯 *Objetivo Principal:*
- Auxiliar estudantes de ADS na compreensão de conceitos técnicos.
- Responder dúvidas sobre programação, banco de dados, engenharia de software e análise de sistemas
- Servir como estudo de caso para implementação de IA em ambientes educacionais.

🛠️ *Funcionalidades:*
✅ Respostas técnicas sobre linguagens de programação (Python, Java, C#, etc.).
✅ Explicações sobre banco de dados (SQL, NoSQL) e modelagem de dados.
✅ Suporte para redes de computadores e segurança da informação.
✅ Informações sobre desenvolvimento de software e boas práticas.
✅ Breves comentários descontraídos ao final das respostas para manter o tom amigável. 🤖✨

📌 *Informações Relevantes para o TCC:*
⌛ *Cronograma:*  
   - Data limite para entrega: 10 de Junho de 2025  
📑 *Normas Técnicas:*  
   - [Acesse as normas ABNT](https://www.fatecoswaldocruz.edu.br/normas-tcc)  
👨‍🏫 *Orientação:*  
   - Professor orientador: Nilton Mattos  
   - Contato: niltoncmattos@yahoo.com.br  

📢 *Observação:*  
Todas as interações são registradas de forma anônima para fins de pesquisa e avaliação do sistema.  
"""

# --- 🔹 Configuração de Log ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# --- 🔹 Função para Consultar a API da IA ---
async def get_ai_response(prompt: str) -> str:
    """
    Consulta a API OpenRouter para obter uma resposta baseada na IA.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/seu-usuario/seu-bot-ads",
        "X-Title": "Bot de ADS",
    }
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
            
    except httpx.TimeoutException:
        logger.error("⏳ Timeout na API OpenRouter")
        return "⚠️ O servidor demorou muito para responder. Tente novamente mais tarde!"
    except Exception:
        logger.error(f"❌ Erro na API: {traceback.format_exc()}")
        return "❌ Houve um problema ao acessar a IA. Use /tcc para mais informações."

# --- 🔹 BANCO DE DADOS (SQLite) ---
def init_db():
    """
    Inicializa o banco de dados SQLite e cria as tabelas necessárias.
    """
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_interaction TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado!") 

# --- 🔹 Handlers (Respostas do Bot) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mensagem de boas-vindas quando o usuário inicia o bot.
    """
    welcome_msg = (
        "👋 *Assistente ADS*\n\n"
        "Digite sua dúvida ou use os comandos abaixo:\n"
        "📌 /tcc - Informações sobre o TCC\n"
        "📌 /sobre - Detalhes do projeto\n\n"
        "Exemplo de pergunta: \"Como fazer um diagrama de classes?\""
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def sobre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Exibe informações sobre o projeto de TCC e sua tecnologia.
    """
    sobre_msg = (
        "🎓 *PROJETO DE TCC - ADS*\n\n"
        "🧑‍💻 *Desenvolvido por:* Francisco F. Dantas\n"
        "👨‍🏫 *Orientação:* Prof. Nilton Mattos\n"
        "📆 *Entrega:* Junho/2025\n\n"
        "🤖 *Tecnologias:* Python, Telegram API, OpenRouter AI, Render (Cloud)\n\n"
        "🔗 *GitHub:* [Clique aqui](https://github.com/frncisc0)\n"
        "📧 *Contato:* franciscofreitas9022@gmail.com"
    )
    await update.message.reply_text(sobre_msg, parse_mode="Markdown", disable_web_page_preview=True)

async def tcc_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Retorna informações sobre prazos e normas do TCC.
    """
    info = (
        "📘 *TCC - Informações Oficiais*\n\n"
        "⏳ *Prazo Final:* 10/06/2025\n"
        "📑 *Normas ABNT:* [Acesse aqui](https://www.fatecoswaldocruz.edu.br/normas-tcc)\n"
        "👨‍🏫 *Orientador:* Prof. Nilton\n"
        "📌 *Requisitos:* Artigo acadêmico, documentação do sistema e apresentação pública.\n\n"
        "💡 Para dúvidas, envie sua pergunta!"
    )
    await update.message.reply_text(info, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa as mensagens enviadas pelo usuário e retorna respostas da IA.
    """
    try:
        user_msg = update.message.text
        logger.info(f"📩 Mensagem recebida: {user_msg}")

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = await get_ai_response(user_msg)
        await update.message.reply_text(response)

    except Exception:
        logger.error(f"❌ Erro no handler: {traceback.format_exc()}")
        await update.message.reply_text("⚠️ Ocorreu um erro. Tente novamente mais tarde.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Captura erros inesperados e evita que o bot pare de funcionar.
    """
    logger.error(f"⚠️ Erro não tratado: {context.error}", exc_info=True)
    await update.message.reply_text("⚠️ Ocorreu um erro inesperado. Já estamos resolvendo!")

# --- 🔹 Configuração Principal do Bot ---
def main():
    init_db()
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tcc", tcc_info))
    application.add_handler(CommandHandler("sobre", sobre))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("🚀 Bot iniciado com sucesso!")
    application.run_polling()

if __name__ == "__main__":
    main()
