import logging
import os
import re
import asyncio
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
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

# --- Configurações ---
class Config:
    DB_PATH = os.getenv("DB_PATH", "db_bot_ads.sqlite")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

class ConversationStates:
    NAME, RA = range(2)

class Messages:
    WELCOME = """👋 *Bem-vindo ao Assistente ADS!*

Sou um bot educacional criado para ajudar estudantes do curso de *Análise e Desenvolvimento de Sistemas*.

🎯 *O que eu posso fazer por você?*
• Responder dúvidas técnicas sobre programação, banco de dados, engenharia de software e mais.
• Compartilhar informações sobre o TCC e o projeto.
• Disponibilizar conteúdos complementares sobre o TCC, como podcast e o arquivo da documentação."""
    
    PROCESSING = "🤖 Processando sua dúvida com inteligência artificial..."
    NOT_REGISTERED = "👤 Você ainda não está cadastrado. Envie /start para iniciar o cadastro."
    INVALID_NAME = "Nome inválido. Por favor, digite seu nome completo:"
    INVALID_RA = "RA inválido. Por favor, insira 4 dígitos:"
    RA_ALREADY_REGISTERED = "Este RA já está cadastrado por outro usuário. Por favor, insira um RA válido ou entre em contato com o suporte." # Nova mensagem
    REGISTRATION_SUCCESS = "✅ Cadastro realizado com sucesso!"
    REGISTRATION_ERROR = "❌ Algo deu errado no cadastro. Envie /start para reiniciar."

# --- Validação de ambiente ---
def validate_environment() -> None:
    """Valida se todas as variáveis de ambiente necessárias estão definidas."""
    required_vars = ["OPENROUTER_API_KEY", "TELEGRAM_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        raise EnvironmentError(f"Variáveis obrigatórias não definidas: {missing_vars}")

# --- Gerenciamento de Banco de Dados ---
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Retorna uma conexão com o banco de dados."""
        return sqlite3.connect(self.db_path)
    
    def init_db(self) -> None:
        """Inicializa o banco de dados com as tabelas necessárias."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alunos (
                        aluno_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        ra TEXT NOT NULL UNIQUE, -- Adicionado UNIQUE para o RA
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
            raise
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao inicializar o banco: {e}")
            raise
    
    def register_user(self, aluno_id: int, name: str, ra: str) -> bool:
        """Registra um usuário no banco de dados."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO alunos (aluno_id, name, ra)
                    VALUES (?, ?, ?);
                """, (aluno_id, name, ra))
                conn.commit()
                logger.info(f"👤 Cadastro/atualização de usuário: {name} (RA: {ra}) - ID: {aluno_id}")
                return True
        except sqlite3.Error as e:
            # Captura a exceção de RA duplicado se o UNIQUE constraint falhar
            if "UNIQUE constraint failed: alunos.ra" in str(e):
                logger.warning(f"❌ Tentativa de registro com RA duplicado: {ra} para aluno_id {aluno_id}")
                return False # Indica falha devido a RA duplicado
            logger.error(f"❌ Erro ao registrar o usuário {name} (ID: {aluno_id}): {e}")
            return False
    
    def is_user_registered(self, aluno_id: int) -> bool:
        """Verifica se um usuário está registrado."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ra FROM alunos WHERE aluno_id = ?", (aluno_id,))
                result = cursor.fetchone()
                return result is not None and result[0] is not None
        except sqlite3.Error as e:
            logger.error(f"❌ Erro ao verificar se o usuário {aluno_id} está registrado: {e}")
            return False

    def is_ra_registered(self, ra: str, current_aluno_id: Optional[int] = None) -> bool:
        """
        Verifica se um RA já está registrado no banco de dados,
        opcionalmente ignorando o aluno_id atual.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if current_aluno_id:
                    cursor.execute("SELECT 1 FROM alunos WHERE ra = ? AND aluno_id != ?", (ra, current_aluno_id))
                else:
                    cursor.execute("SELECT 1 FROM alunos WHERE ra = ?", (ra,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"❌ Erro ao verificar duplicidade de RA '{ra}': {e}")
            return False
    
    def get_user_info(self, aluno_id: int) -> Optional[Dict[str, Any]]:
        """Retorna informações completas do usuário."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT aluno_id, name, ra FROM alunos WHERE aluno_id = ?", 
                    (aluno_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return {
                        "aluno_id": result[0],
                        "name": result[1], 
                        "ra": result[2]
                    }
                return None
        except sqlite3.Error as e:
            logger.error(f"❌ Erro ao buscar usuário {aluno_id}: {e}")
            return None
    
    def register_interaction(self, aluno_id: int) -> None:
        """Registra uma interação do usuário."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO interacoes (aluno_id) VALUES (?)",
                    (aluno_id,)
                )
                conn.commit()
                logger.info(f"Interação registrada para aluno_id: {aluno_id}")
        except sqlite3.Error as e:
            logger.error(f"❌ Erro ao registrar interação para aluno_id {aluno_id}: {e}")

# --- Validação de dados ---
def validate_name(name: str) -> Tuple[bool, str]:
    """Valida o nome do usuário com feedback específico."""
    name = name.strip()
    
    if len(name) < 3:
        return False, "Nome muito curto. Digite pelo menos 3 caracteres."
    
    # Atualizado para permitir espaços
    if not re.match(r"^[A-Za-zÀ-ÿ\s]{3,50}$", name):
        return False, "Nome deve conter apenas letras e espaços."
    
    forbidden_words = ["oi", "olá", "ola", "teste", "admin", "bot"]
    if name.lower() in forbidden_words:
        return False, "Por favor, digite seu nome real."
    
    return True, ""

def validate_ra(ra: str) -> Tuple[bool, str]:
    """Valida o RA do usuário."""
    ra = ra.strip()
    
    if not ra.isdigit():
        return False, "RA deve conter apenas números."
    
    if len(ra) != 4:
        return False, "RA deve ter exatamente 4 dígitos."
    
    return True, ""

# --- Gerenciamento de IA ---
class AIManager:
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.system_prompt = """Você é o Assistente ADS, um chatbot educacional criado para apoiar estudantes de Análise e Desenvolvimento de Sistemas (ADS).
Seu objetivo é fornecer respostas técnicas e precisas sobre temas relacionados ao curso, promovendo o aprendizado interativo — e, claro, com um toque de bom humor, com analogias para aliviar a tensão da faculdade!

🎯 Objetivo Principal:
- Auxiliar estudantes de ADS na compreensão de conceitos técnicos.
- Responder dúvidas sobre programação, banco de dados, engenharia de software e análise de sistemas.
- Servir como estudo de caso para implementação de IA em ambientes educacionais.
- Se a pergunta estiver fora do escopo EXCLUSIVO do curso de Análise e Desenvolvimento de Sistemas (ADS), responda educadamente
 (com simpatia e leveza): "Desculpe, só posso responder dúvidas relacionadas à área de TI."
"""
    
    async def get_response(self, prompt: str, max_retries: int = 3) -> str:
        """Obtém resposta da IA com retry e validação."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/frncisc0",
            "X-Title": "Bot de ADS"
        }

        payload = {
            "model": "deepseek/deepseek-chat",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(self.api_url, headers=headers, json=payload)
                    response.raise_for_status()
                    
                    response_data = response.json()
                    if "choices" not in response_data or not response_data["choices"]:
                        return "❌ Resposta inválida da IA."
                    
                    return response_data["choices"][0]["message"]["content"]
                    
            except httpx.TimeoutException:
                if attempt == max_retries - 1:
                    return "⏱️ Timeout na IA. Tente uma pergunta mais simples."
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial
                
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ Erro HTTP ao acessar a IA: {e.response.status_code} - {e.response.text}")
                if attempt == max_retries - 1:
                    return "❌ A IA está indisponível no momento. Tente novamente mais tarde."
                await asyncio.sleep(2 ** attempt)
                
            except httpx.RequestError as e:
                logger.error(f"❌ Erro de requisição ao acessar a IA: {e}")
                if attempt == max_retries - 1:
                    return "❌ Erro de conexão com a IA. Verifique sua internet ou tente mais tarde."
                await asyncio.sleep(2 ** attempt)
                
            except (KeyError, IndexError, TypeError) as e:
                logger.error(f"❌ Estrutura de resposta inesperada da IA: {e}")
                return "❌ Erro ao processar resposta da IA."
                
            except Exception as e:
                logger.error(f"❌ Erro inesperado ao acessar a IA: {e}")
                if attempt == max_retries - 1:
                    return f"❌ Erro inesperado ao acessar a IA: {e}"
                await asyncio.sleep(2 ** attempt)

# --- Instâncias globais ---
db_manager = DatabaseManager(Config.DB_PATH)
ai_manager = AIManager(Config.OPENROUTER_API_KEY, Config.OPENROUTER_API_URL)

# --- Handlers do Bot ---
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o processo de cadastro pedindo o nome."""
    context.user_data["em_cadastro"] = True
    await update.message.reply_text("Olá! Qual o seu nome?")
    return ConversationStates.NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa o nome fornecido pelo usuário."""
    name = update.message.text.strip()
    is_valid, error_message = validate_name(name)
    
    if not is_valid:
        await update.message.reply_text(error_message)
        return ConversationStates.NAME
    
    context.user_data["name"] = name
    context.user_data["em_cadastro"] = True
    await update.message.reply_text(f"Legal, {name}! Agora me diga seu RA (4 dígitos):")
    return ConversationStates.RA

async def get_ra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa o RA fornecido pelo usuário."""
    ra = update.message.text.strip()
    user_id = update.message.from_user.id

    is_valid, error_message = validate_ra(ra)
    
    if not is_valid:
        await update.message.reply_text(error_message)
        return ConversationStates.RA
    
    # --- NOVA CHECAGEM DE DUPLICIDADE DE RA ---
    if db_manager.is_ra_registered(ra, current_aluno_id=user_id):
        logger.info(f"Tentativa de cadastro com RA duplicado: {ra} por user_id {user_id}")
        await update.message.reply_text(Messages.RA_ALREADY_REGISTERED)
        # Opcional: Reiniciar o cadastro ou pedir outro RA
        # Para forçar o reinício do cadastro, descomente a linha abaixo e remova 'return ConversationStates.RA'
        # context.user_data.pop("em_cadastro", None)
        # return ConversationHandler.END # Encerra a conversa atual
        return ConversationStates.RA # Permite que o usuário tente digitar o RA novamente
    # --- FIM DA NOVA CHECAGEM ---
    
    name = context.user_data.get("name")
    
    if not name:
        logger.warning(f"Cadastro falhou para user_id {user_id}: nome não encontrado em context.user_data")
        await update.message.reply_text(Messages.REGISTRATION_ERROR)
        return ConversationHandler.END
    
    success = db_manager.register_user(user_id, name, ra)
    context.user_data.pop("em_cadastro", None)
    
    if success:
        await update.message.reply_text(Messages.REGISTRATION_SUCCESS)
        await update.message.reply_text(
            f"👋 Assistente ADS - Olá {name}! Como posso ajudar?\n\n"
            "📌 Comandos disponíveis:\n/start - Reiniciar\n/sobre - Sobre o projeto\n/tcc - Informações do TCC"
        )
    else:
        # Este 'else' será acionado se o register_user falhar por alguma outra razão (ex: erro de DB)
        # Para RA duplicado, já foi tratado acima.
        await update.message.reply_text("❌ Erro ao realizar cadastro. Tente novamente mais tarde.")
    
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - inicia o bot ou cadastro."""
    user_id = update.message.from_user.id
    user_first_name = update.message.from_user.first_name

    if db_manager.is_user_registered(user_id):
        user_info = db_manager.get_user_info(user_id)
        display_name = user_info["name"] if user_info else user_first_name
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
        await update.message.reply_text(Messages.WELCOME, parse_mode="Markdown")
        return await ask_name(update, context)

async def sobre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /sobre: Exibe informações sobre o projeto de TCC."""
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
    """Comando /tcc: Exibe informações detalhadas do TCC."""
    link_podcast = "https://drive.google.com/file/d/16XpXbCgUhRczxrZ-N8y5TVA7JfBqb1uo/view?usp=drive_link"
    link_documentacao = "https://drive.google.com/file/d/1moPhStmyRY7vRt5POkkZZ-fWdnkoamX7/view?usp=drive_link"

    await update.message.reply_text(
        "📚 *Detalhes do nosso TCC: O Assistente ADS!*\n\n"
        "🗓️ *Prazo Final de Entrega:* 20 de Junho de 2025\n"
        "👨‍🏫 *Orientador:* Professor Nilton Mattos\n\n"
        "Este projeto busca aplicar conceitos de IA e desenvolvimento de bots para criar uma ferramenta educacional interativa.\n\n"
        "--- \n\n"
        "🎧 *Quer saber mais sobre a jornada do projeto?*\n"
        "Ouça nosso Podcast exclusivo! Ele detalha o processo de desenvolvimento e os desafios superados.\n"
        f"➡️ [Baixe e Ouça o Podcast Completo Aqui!]({link_podcast}) 🎧\n\n"
        "📄 *Documentação Completa:* \n"
        "Acesse todos os detalhes técnicos, diagramas e explicação da implementação do projeto.\n"
        f"➡️ [Baixe a Documentação do TCC Aqui!]({link_documentacao}) 📑",
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status: Verifica o status do sistema."""
    try:
        with db_manager.get_connection() as conn:
            conn.execute("SELECT 1")
        await update.message.reply_text("✅ Conexão com o banco SQLite funcionando!")
    except sqlite3.Error as e:
        logger.error(f"Erro ao verificar status do banco: {e}")
        await update.message.reply_text("⚠️ Erro ao acessar o banco de dados.")
    except Exception as e:
        logger.error(f"Erro inesperado ao verificar status do banco: {e}")
        await update.message.reply_text("⚠️ Erro inesperado ao verificar o banco de dados.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens dos usuários."""
    user_id = update.message.from_user.id
    
    # Ignora mensagens durante cadastro
    if context.user_data.get("em_cadastro"):
        return
    
    # Verifica se usuário está registrado
    if not db_manager.is_user_registered(user_id):
        await update.message.reply_text(Messages.NOT_REGISTERED)
        return
    
    user_msg = update.message.text.strip()
    db_manager.register_interaction(user_id)
    
    await update.message.reply_text(Messages.PROCESSING)
    response = await ai_manager.get_response(user_msg)
    await update.message.reply_text(f"{response}\n\n📚 Espero ter ajudado!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela o processo de cadastro."""
    context.user_data.pop("em_cadastro", None)
    await update.message.reply_text("❌ Cadastro cancelado.")
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde a comandos não reconhecidos."""
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
    """Função principal que inicializa e executa o bot."""
    try:
        # Valida variáveis de ambiente
        validate_environment()
        
        # Inicializa o banco de dados
        logger.info("Inicializando banco de dados...")
        
        # Cria a aplicação do bot
        application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        
        # Configura o handler de conversação para cadastro
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                ConversationStates.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                ConversationStates.RA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ra)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        
        # Adiciona todos os handlers
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("sobre", sobre))
        application.add_handler(CommandHandler("tcc", tcc_info))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.COMMAND, unknown))
        
        logger.info("🚀 Bot iniciando polling...")
        application.run_polling()
        
    except EnvironmentError as e:
        logger.error(f"❌ Erro de configuração: {e}")
        print(f"❌ Erro de configuração: {e}")
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao iniciar o bot: {e}")
        print(f"❌ Erro inesperado ao iniciar o bot: {e}")

if __name__ == "__main__":
    main()