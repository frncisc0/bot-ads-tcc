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

# --- Verificação e Instalação de Dependências ---
try:
    from dotenv import load_dotenv
except ImportError:
    import subprocess
    print("Instalando python-dotenv...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv

# --- Configuração Inicial ---
load_dotenv()

# Variáveis de ambiente
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_API_KEY:
    raise ValueError(
        "Configure suas variáveis de ambiente no arquivo .env:\n"
        "TELEGRAM_TOKEN=seu_token_aqui\n"
        "OPENROUTER_API_KEY=sua_chave_aqui"
    )

# --- Constantes ---
# --- Configurações da API ---
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM_PROMPT = """Você é o Assistente IA, um sistema de inteligência artificial desenvolvido para o Telegram como parte do Trabalho de Conclusão de Curso (TCC) de Francisco Dantas
no curso de Análise e Desenvolvimento de Sistemas. Que as vezes fala alguma coisa engraçada no final das frases.

Objetivo principal:
- Fornecer suporte acadêmico para disciplinas do curso de ADS
- Auxiliar na compreensão de conceitos técnicos
- Servir como estudo de caso para implementação de IA em ambientes educacionais

Funcionalidades:
✓ Respostas técnicas sobre programação (Python, Java, C#, etc.)
✓ Explicações sobre banco de dados, redes e engenharia de software
✓ Suporte para metodologias ágeis e boas práticas de desenvolvimento

Informações relevantes para o TCC:
⌛ Cronograma: 
   - Data limite para entrega: 30 de Junho de 2025
📑 Normas técnicas: 
   - [Documentação completa disponível aqui](https://exemplo.com/normas)
👨‍🏫 Orientação: 
   - Professor orientador: Nilton Mattos
   - Contato: niltoncmattos@yahoo.com.br

Observação: Todas as interações serão registradas de forma anônima,
para fins de pesquisa e avaliação do sistema.
"""

# --- Configuração de Log ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Funções da API ---
async def get_ai_response(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/seu-usuario/seu-bot-ads",
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
        logger.error("Timeout na API OpenRouter")
        return "⏳ O servidor demorou muito para responder. Tente novamente!"
    except Exception as e:
        logger.error(f"Erro na API: {traceback.format_exc()}")
        return "❌ Problema temporário. Use /tcc para informações locais."
    
# --- BANCO DE DADOS ---
def init_db():
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
    print("Banco de dados inicializado!") 

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
         "👋 *Assistente ADS*\n"
        "Digite sua dúvida ou use:\n"
        "/tcc - Informações TCC\n"
        "/sobre - Detalhes do projeto\n\n"
        "Ex: \"Como fazer um diagrama de classes?\""
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def sobre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sobre_msg = (
        "🎓 *PROJETO DE TCC - ADS*\n"
        "Faculdade Oswaldo Cruz\n\n"
        
        "🧑‍💻 *Desenvolvido por:*\n"
        "Francisco F. Dantas (RA: 7523006)\n\n"    
        
        "👨‍🏫 *Orientação:*\n"
        "Prof. Nilton\n\n"
        
        "📆 *Cronograma:*\n"
        "Previsão de conclusão: Junho/2025\n\n"
        
        "🤖 *Tecnologias Utilizadas:*\n"
        "- Plataforma: Telegram Bot API\n"
        "- IA: DeepSeek Chat (via OpenRouter)\n"
        "- Linguagem: Python 3.12\n"
        "- Infraestrutura: Render (Cloud)\n\n"
        
        "📝 *Objetivos Acadêmicos:*\n"
        "1. Integrar IA generativa no apoio educacional\n"
        "2. Automatizar respostas sobre conteúdo de ADS\n"
        "3. Demonstrar aplicações práticas de NLP\n\n"
        
        "🔗 *Repositório:* [GitHub](https://github.com/frncisc0)\n"
        "📧 *Contato:* franciscofreitas9022@gmail.com"
    )
    await update.message.reply_text(sobre_msg, parse_mode="Markdown", 
                                 disable_web_page_preview=True)

async def tcc_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = (
        "📘 *TCC - Informações Oficiais*\n\n"
        "⏳ *Prazo de Entrega:* 10/06/2025\n"
        "📑 *Normas ABNT:* [Manual Completo](https://www.fatecoswaldocruz.edu.br/normas-tcc)\n"
        "👨‍🏫 *Orientador:* Prof. Dr. Nilton\n\n"
        "📌 *Requisitos Técnicos:*\n"
        "- Documentação completa do sistema\n"
        "- Artigo acadêmico (15-20 páginas)\n"
        "- Apresentação pública\n\n"
        "💡 *Dúvidas?* Envie sua pergunta ou use /sobre para detalhes do projeto."
    )
    await update.message.reply_text(info, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_msg = update.message.text
        logger.info(f"Mensagem recebida: {user_msg}")

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        response = await get_ai_response(user_msg)
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Erro no handler: {traceback.format_exc()}")
        await update.message.reply_text("🔧 Erro interno. Tente novamente mais tarde.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Erro não tratado: {context.error}", exc_info=True)
    await update.message.reply_text("⚠️ Ocorreu um erro inesperado. Já estamos resolvendo!")

# --- Configuração Principal ---
def main():
    #Inicializa o banco de dados antes do bot
    init_db()

    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    handlers = [
        CommandHandler("start", start),
        CommandHandler("tcc", tcc_info),
         CommandHandler("sobre", sobre),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    ]
    
    for handler in handlers:
        application.add_handler(handler)
    
    application.add_error_handler(error_handler)
    logger.info("Bot iniciado com sucesso!")
    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Falha na inicialização: {traceback.format_exc()}")
        sys.exit(1)