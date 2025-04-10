import logging
import os
import re
from datetime import datetime
import httpx
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
import psycopg2
from psycopg2 import sql

load_dotenv()

# --- Configuração de log ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Estados da conversa ---
NAME, RA = range(2)

# --- Banco de dados PostgreSQL ---
def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost")
    )

def init_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                name TEXT,
                ra TEXT,
                first_interaction TIMESTAMP
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Banco de dados PostgreSQL inicializado!")
    except Exception as e:
        print(f"❌ Erro ao inicializar o banco: {e}")

def is_user_registered(user_id: int) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ra FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result is not None and result[0] is not None
    except Exception as e:
        print(f"❌ Erro ao verificar usuário: {e}")
        return False

def register_user(user_id: int, name: str, ra: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, name, ra, first_interaction)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                name = EXCLUDED.name,
                ra = EXCLUDED.ra,
                first_interaction = NOW();
        """, (user_id, name, ra))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao registrar usuário: {e}")

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
            if response.status_code != 200:
                return "❌ A IA está indisponível no momento. Tente novamente mais tarde."
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

    if not re.match(r"^[A-Za-zÀ-ÿ\s]+$", name):
        await update.message.reply_text("Nome inválido. Por favor, use apenas letras e espaços:")
        return NAME

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
        "📄 Documentação oficial: [Clique aqui para baixar](https://link-para-documento.pdf)\n"
        "👨‍🏫 Orientador: Prof. Nilton",
        parse_mode="Markdown"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Seja bem-vindo ao *Assistente ADS* — seu bot educacional para dúvidas de *Análise e Desenvolvimento de Sistemas*!\n\n"
        "📘 Aqui você pode:\n"
        "✅ Tirar dúvidas sobre programação, banco de dados, redes e muito mais!\n\n"
        "🚀 *O que deseja fazer?*\n"
        "1️⃣ Envie *qualquer mensagem* para iniciar o cadastro (caso ainda não tenha feito).\n"
        "2️⃣ Use os comandos abaixo para navegar:\n\n"
        "📌 /sobre — Informações do projeto\n"
        "📌 /tcc — Regras e prazos do TCC\n",
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_connection()
        conn.close()
        await update.message.reply_text("✅ Bot funcionando normalmente e conectado ao banco de dados.")
    except:
        await update.message.reply_text("⚠️ Problema ao conectar com o banco de dados.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_user_registered(user_id):
        return await ask_name(update, context)

    user_msg = update.message.text.strip()
    await update.message.reply_text("🤖 Processando sua dúvida com inteligência artificial...")
    response = await get_ai_response(user_msg)
    await update.message.reply_text(f"{response}\n\n📚 Espero ter ajudado! Me mande outra dúvida se quiser.")

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
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.run_polling()

if __name__ == "__main__":
    main()