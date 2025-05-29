import logging
import os
import re
from datetime import datetime
import httpx
import sqlite3
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

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração de log ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Estados da conversa ---
NAME, RA = range(2)

# --- Banco de dados SQLite ---
DB_PATH = "db_bot_ads.sqlite"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alunos (
                    aluno_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    ra TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aluno_id INTEGER NOT NULL,
                    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (aluno_id) REFERENCES alunos(aluno_id)
                );
            """)
            conn.commit()
            logger.info("✅ Banco de dados inicializado com as tabelas 'alunos' e 'interacoes'")
    except sqlite3.Error as e:
        logger.error(f"❌ Erro de SQLite ao inicializar o banco: {e}")
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao inicializar o banco: {e}")

def registrar_interacao(aluno_id: int) -> None:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO interacoes (aluno_id) VALUES (?)",
                (aluno_id,)
            )
            conn.commit()
            logger.info(f"Interação registrada para aluno_id: {aluno_id}")
    except sqlite3.Error as e:
        logger.error(f"❌ Erro ao registrar interação para aluno_id {aluno_id}: {e}")

def is_user_registered(aluno_id: int) -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ra FROM alunos WHERE aluno_id = ?", (aluno_id,))
            result = cursor.fetchone()
            return result is not None and result[0] is not None
    except sqlite3.Error as e:
        logger.error(f"❌ Erro ao verificar se o usuário {aluno_id} está registrado: {e}")
        return False

def register_user(aluno_id: int, name: str, ra: str):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO alunos (aluno_id, name, ra)
                VALUES (?, ?, ?);
            """, (aluno_id, name, ra))
            conn.commit()
            logger.info(f"👤 Cadastro/atualização de usuário: {name} (RA: {ra}) - ID: {aluno_id}")
    except sqlite3.Error as e:
        logger.error(f"❌ Erro ao registrar o usuário {name} (ID: {aluno_id}): {e}")

# --- Configuração da API OpenRouter ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """Você é o Assistente ADS, um chatbot educacional criado para apoiar estudantes de Análise e Desenvolvimento de Sistemas (ADS).
Seu objetivo é fornecer respostas técnicas e precisas sobre temas relacionados ao curso, promovendo o aprendizado interativo  — e, claro, com um toque de bom humor para aliviar a tensão da faculdade!.

🎯 Objetivo Principal:
- Auxiliar estudantes de ADS na compreensão de conceitos técnicos.
- Responder dúvidas sobre programação, banco de dados, engenharia de software e análise de sistemas.
- Servir como estudo de caso para implementação de IA em ambientes educacionais.
- Se a pergunta estiver fora desse escopo, responda educadamente (com simpatia e leveza): \"Desculpe, só posso responder dúvidas relacionadas à área de TI.\"
"""

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
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Erro HTTP ao acessar a IA: {e.response.status_code} - {e.response.text}")
        return "❌ A IA está indisponível no momento. Tente novamente mais tarde."
    except httpx.RequestError as e:
        logger.error(f"❌ Erro de requisição ao acessar a IA: {e}")
        return "❌ Erro de conexão com a IA. Verifique sua internet ou tente mais tarde."
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao acessar a IA: {e}")
        return f"❌ Erro inesperado ao acessar a IA: {e}"

# --- Conversa com o usuário (Fluxo de Cadastro) ---
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["em_cadastro"] = True
    await update.message.reply_text("Olá! Qual o seu nome?")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if (
        not re.match(r"^[A-Za-zÀ-ÿ\s]{3,}$", name)
        or name.lower() in ["oi", "olá", "ola", "teste"]
    ):
        await update.message.reply_text("Nome inválido. Por favor, digite seu nome completo:")
        return NAME
    context.user_data["name"] = name
    context.user_data["em_cadastro"] = True
    await update.message.reply_text(f"Legal, {name}! Agora me diga seu RA (4 dígitos):")
    return RA

async def get_ra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ra = update.message.text.strip()
    if not ra.isdigit() or len(ra) != 4:
        await update.message.reply_text("RA inválido. Por favor, insira 4 dígitos:")
        return RA
    user_id = update.message.from_user.id
    name = context.user_data.get("name")
    if not name:
        logger.warning(f"Cadastro falhou para user_id {user_id}: nome não encontrado em context.user_data")
        await update.message.reply_text("❌ Algo deu errado no cadastro. Envie /start para reiniciar.")
        return ConversationHandler.END
    register_user(user_id, name, ra)
    context.user_data.pop("em_cadastro", None)
    await update.message.reply_text("✅ Cadastro realizado com sucesso!")
    await update.message.reply_text(
        f"👋 Assistente ADS - Olá {name}! Como posso ajudar?\n\n"
        "📌 Comandos disponíveis:\n/start - Reiniciar\n/sobre - Sobre o projeto\n/tcc - Informações do TCC"
    )
    return ConversationHandler.END

# --- Comandos do Bot ---
async def sobre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /sobre: Exibe informações sobre o projeto de TCC.
    """
    await update.message.reply_text(
        "👋 Olá! Sou o Assistente ADS, um projeto de TCC desenvolvido com carinho para aprimorar o aprendizado em Análise e Desenvolvimento de Sistemas!\n\n"
        "👨‍💻 Desenvolvedor: Francisco F. Dantas\n"
        "🗓️ Previsão de Entrega: Junho/2025\n\n"
        "✨ Minhas tecnologias base:\n"
        "- Python: Para a lógica principal e automação.\n"
        "- Telegram API: Para a interface de chat.\n"
        "- OpenRouter: Para a inteligência artificial que me dá minhas respostas.\n"
        "- SQLite: Para armazenar dados importantes, como os seus!\n\n"
        "Meu objetivo é ser uma ferramenta de apoio para estudantes como você! 😊"
    )

async def tcc_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /tcc: Exibe informações detalhadas do TCC, um link para o podcast
    e um link para a documentação.
    Usa Markdown para formatar os links.
    """
    # Link do podcast corrigido para download direto
    link_podcast = "https://drive.google.com/uc?export=download&id=1QAd9PBF4Ynf7dwOYe6huUH9yxPAcWHgL"
    
    # Link da documentação corrigido para download direto
    link_documentacao = "https://drive.google.com/uc?export=download&id=1Vwa-tyskqp6y0P8jfGwpujwHHd1_2vOx" 

    await update.message.reply_text(
        "📚 *Detalhes do nosso TCC: O Assistente ADS!*\n\n"
        "🗓️ *Prazo Final de Entrega:* 20 de Junho de 2025\n"
        "👨‍🏫 *Orientador:* Professor Nilton\n\n"
        "Este projeto busca aplicar conceitos de IA e desenvolvimento de bots para criar uma ferramenta educacional interativa.\n\n"
        "--- \n\n" # Linha divisória opcional
        "🎧 *Quer saber mais sobre a jornada do projeto?*\n"
        "Ouça nosso Podcast exclusivo! Ele detalha o processo de desenvolvimento e os desafios superados.\n"
        "➡️ [Baixe e Ouça o Podcast Completo Aqui!](" + link_podcast + ") 🎧\n\n"
        "📄 *Documentação Completa:* \n"
        "Acesse todos os detalhes técnicos, diagramas e explicação da implementação do projeto.\n"
        "➡️ [Baixe a Documentação do TCC Aqui!](" + link_documentacao + ") 📑",
        parse_mode="Markdown"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_first_name = update.message.from_user.first_name

    full_welcome_message = (
        f"👋 *Bem-vindo ao Assistente ADS!*\n\n"
        "Sou um bot educacional criado para ajudar estudantes do curso de *Análise e Desenvolvimento de Sistemas*.\n\n"
        "🎯 *O que eu posso fazer por você?*\n"
        "• Responder dúvidas técnicas sobre programação, banco de dados, engenharia de software e mais.\n"
        "• Compartilhar informações sobre o TCC e o projeto.\n"
        "• Disponibilizar conteúdos complementares sobre o TCC, como podcast e o arquivo da documentação.\n\n"
    )

    if is_user_registered(user_id):
        display_name = context.user_data.get('name', user_first_name)
        logger.info(f"Usuário {user_id} ({display_name}) já cadastrado. Saudar e apresentar comandos.")
        await update.message.reply_text(
            f"Olá novamente, {display_name}!\n\n"
            "Como posso ajudar hoje?\n\n"
            "📌 Comandos disponíveis:\n/start - Reiniciar\n/sobre - Sobre o projeto\n/tcc - Informações do TCC",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    else:
        logger.info(f"Usuário {user_id} ({user_first_name}) não cadastrado. Iniciando fluxo de cadastro.")
        await update.message.reply_text(full_welcome_message, parse_mode="Markdown")
        return await ask_name(update, context)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        await update.message.reply_text("✅ Conexão com o banco SQLite funcionando!")
    except sqlite3.Error as e:
        logger.error(f"Erro ao verificar status do banco: {e}")
        await update.message.reply_text("⚠️ Erro ao acessar o banco de dados.")
    except Exception as e:
        logger.error(f"Erro inesperado ao verificar status do banco: {e}")
        await update.message.reply_text("⚠️ Erro inesperado ao verificar o banco de dados.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if context.user_data.get("em_cadastro"):
        return
    if not is_user_registered(user_id):
        await update.message.reply_text("👤 Você ainda não está cadastrado. Envie /start para iniciar o cadastro.")
        return
    user_msg = update.message.text.strip()
    registrar_interacao(user_id)
    await update.message.reply_text("🤖 Processando sua dúvida com inteligência artificial...")
    response = await get_ai_response(user_msg)
    await update.message.reply_text(f"{response}\n\n📚 Espero ter ajudado!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("em_cadastro", None)
    await update.message.reply_text("❌ Cadastro cancelado.")
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Comando não reconhecido.\n\n"
        "👉 Para ver os comandos disponíveis, toque no botão *Menu* "
        "à esquerda do campo de digitação, ou use um dos seguintes comandos diretamente:\n\n"
        "/start – Iniciar atendimento\n"
        "/sobre – Informações sobre o projeto\n"
        "/tcc – Detalhes do TCC e acesso ao podcast",
        parse_mode="Markdown"
    )

def main():
    init_db()
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            RA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ra)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("sobre", sobre))
    application.add_handler(CommandHandler("tcc", tcc_info))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    logger.info("Bot iniciando polling...")
    application.run_polling()

if __name__ == "__main__":
    main()