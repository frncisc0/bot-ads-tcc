import logging
import os
import sqlite3
from datetime import datetime
import httpx
import traceback
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv
load_dotenv()

# --- Configuração de log ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Estados da conversa ---
NAME, RA = range(2)

# --- Banco de dados ---
def init_db():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            ra TEXT,
            first_interaction TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def is_user_registered(user_id: int) -> bool:
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ra FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None and result[0] is not None


def register_user(user_id: int, name: str, ra: str):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, name, ra, first_interaction)
        VALUES (?, ?, ?, ?)
    """, (user_id, name, ra, datetime.now()))
    conn.commit()
    conn.close()


def reset_user(user_id: int):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# --- Configuração da API OpenRouter ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """Você é o Assistente ADS, um chatbot educacional criado para apoiar estudantes de Análise e Desenvolvimento de Sistemas (ADS). 
Seu objetivo é fornecer respostas técnicas e precisas sobre temas relacionados ao curso, promovendo o aprendizado interativo.

🎯 *Objetivo Principal:*
- Auxiliar estudantes de ADS na compreensão de conceitos técnicos.
- Responder dúvidas sobre programação, banco de dados, engenharia de software e análise de sistemas.
- Servir como estudo de caso para implementação de IA em ambientes educacionais.

🛠️ *Funcionalidades:*
✅ Respostas técnicas sobre linguagens de programação (Python, Java, C#, etc.).
✅ Explicações sobre banco de dados (SQL, NoSQL) e modelagem de dados.
✅ Suporte para redes de computadores e segurança da informação.
✅ Informações sobre desenvolvimento de software e boas práticas.
✅ Breves comentários descontraídos ao final das respostas para manter o tom de humor e amigável.  🤖✨
"""


# --- Função para chamar a IA ---
async def get_ai_response(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/frncisc0",
        "X-Title": "Bot de ADS"
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
        return "⏳ O servidor demorou para responder. Tente novamente."
    except Exception as e:
        return f"❌ Ocorreu um erro ao acessar a IA. {e}"


# --- Conversa ---
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Olá! Qual o seu nome?")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    context.user_data["name"] = name
    await update.message.reply_text(f"Legal, {name}! Agora me diga seu RA (4 dígitos):")
    return RA


async def get_ra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ra = update.message.text.strip()
    if not ra.isdigit() or len(ra) != 4:
        await update.message.reply_text("RA inválido. Por favor, insira 4 dígitos:")
        return RA

    user_id = update.message.from_user.id
    name = context.user_data["name"]
    register_user(user_id, name, ra)

    await update.message.reply_text("✅ Cadastro realizado com sucesso!")
    await update.message.reply_text(
        f"👋 Assistente ADS - Olá {name}! Como posso ajudar?\n\n"
        "📌 Use os comandos:\n/start - Reiniciar\n/sobre - Sobre o projeto\n/tcc - Informações do TCC"
    )
    return ConversationHandler.END


# --- Comandos ---
async def sobre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 Projeto de TCC - ADS\n"
        "Desenvolvido por: Francisco F. Dantas\n"
        "Orientação: Prof. Nilton Mattos\n"
        "Entrega: Junho/2025\n\n"
        "Tecnologias: Python, Telegram API, OpenRouter AI, AWS Cloud\n"
        "GitHub: https://github.com/frncisc0"
    )


async def tcc_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 TCC - Informações Oficiais\n"
        "Prazo Final: 10/06/2025\n"
        "Normas ABNT: https://www.fatecoswaldocruz.edu.br/normas-tcc\n"
        "Orientador: Prof. Nilton"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    reset_user(user_id)
    await update.message.reply_text("🔄 Cadastro resetado com sucesso! Envie qualquer mensagem para iniciar novamente o processo de cadastro.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_user_registered(user_id):
        return await ask_name(update, context)

    user_msg = update.message.text.strip()
    await update.message.reply_text("🤖 Processando sua dúvida com inteligência artificial...")
    response = await get_ai_response(user_msg)
    await update.message.reply_text(response)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Cadastro cancelado.")
    return ConversationHandler.END


# --- Inicialização do bot ---
def main():
    from telegram.ext import ApplicationBuilder
    init_db()

    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            RA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ra)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("sobre", sobre))
    application.add_handler(CommandHandler("tcc", tcc_info))
    application.add_handler(CommandHandler("reset", reset))
    application.run_polling()


if __name__ == "__main__":
    main()
