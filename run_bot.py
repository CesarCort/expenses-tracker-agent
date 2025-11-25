import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ChatAction
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types
import base64
import os
import re
from spending_tracker.agent import root_agent
from google.adk.plugins import ReflectAndRetryToolPlugin

# Configuración de logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
load_dotenv("./spending_tracker/.env")
# Crear el runner una vez (singleton)
APP_NAME = "agents"
runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME, plugins=[ReflectAndRetryToolPlugin(max_retries=3)])

# Diccionario para mantener sesiones por usuario
user_sessions: dict[int, str] = {}


def markdown_to_telegram_html(text: str) -> str:
    """Convierte markdown del modelo a HTML válido de Telegram"""
    if not text:
        return text
    
    # Escapar caracteres HTML especiales primero
    # (pero preservar los que ya son tags válidos)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    # Ahora convertir markdown a HTML
    
    # **bold** → <b>bold</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # *italic* → <i>italic</i>
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    
    # __underline__ → <u>underline</u>
    text = re.sub(r'__(.+?)__', r'<u>\1</u>', text)
    
    # _italic_ → <i>italic</i>
    text = re.sub(r'(?<![a-zA-Z])_(.+?)_(?![a-zA-Z])', r'<i>\1</i>', text)
    
    # `code` → <code>code</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    # ```code block``` → <pre>code</pre>
    text = re.sub(r'```(?:\w+)?\n?(.*?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)
    
    # ~~strikethrough~~ → <s>strikethrough</s>
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    
    # [link](url) → <a href="url">link</a>
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    
    return text

async def get_or_create_session(user_id: int) -> str:
    """Obtiene o crea una sesión para el usuario"""
    if user_id not in user_sessions:
        session_id = f"session_{user_id}"
        await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=str(user_id),
            session_id=session_id
        )
        user_sessions[user_id] = session_id
    return user_sessions[user_id]

async def run_agent_and_reply(update: Update, content: types.Content):
    """Ejecuta el agente y envía la respuesta"""
    user_id = update.effective_user.id
    
    try:
        session_id = await get_or_create_session(user_id)
        
        final_response = ""
        async for event in runner.run_async(
            user_id=str(user_id),
            session_id=session_id,
            new_message=content
        ):
            print(f"Event: {event}")
            await update.message.chat.send_action(ChatAction.TYPING)
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text

        if final_response:
            print(f"Final response: {final_response}")
            formatted_text = markdown_to_telegram_html(final_response)
            await update.message.reply_text(formatted_text, parse_mode="HTML")
        else:
            await update.message.reply_text("No pude procesar tu mensaje.")
            
    except Exception as e:
        logging.error(f"Error procesando mensaje: {e}")
        await update.message.reply_text("Ocurrió un error. Intenta nuevamente.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /start"""
    welcome_message = "¡Hola! Soy tu asistente de gastos. Envíame tus gastos o dudas."
    await update.message.reply_text(welcome_message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto"""
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    logging.info(f"Mensaje de texto de {chat_id}: {user_text}")
    
    content = types.Content(
        role='user',
        parts=[types.Part.from_text(text=user_text)]
    )
    
    await run_agent_and_reply(update, content)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja imágenes enviadas por el usuario"""
    chat_id = update.effective_chat.id
    logging.info(f"Imagen recibida de {chat_id}")
    
    # Obtener la foto de mayor resolución
    photo = update.message.photo[-1]
    
    # Descargar la imagen
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()
    
    # Convertir a base64
    image_base64 = base64.b64encode(bytes(image_bytes)).decode('utf-8')
    
    # Crear las partes del mensaje
    parts = [
        types.Part.from_bytes(
            data=bytes(image_bytes),
            mime_type='image/jpeg'
        )
    ]
    
    # Si hay caption (texto junto a la imagen), agregarlo
    if update.message.caption:
        parts.append(types.Part.from_text(text=update.message.caption))
    else:
        # Si no hay caption, agregar instrucción por defecto
        parts.append(types.Part.from_text(text="Analiza esta imagen y extrae la información del gasto."))
    
    content = types.Content(role='user', parts=parts)
    
    await update.message.reply_text("📷 Procesando imagen...")
    await run_agent_and_reply(update, content)

def main():
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # ← Fotos

    logging.info("Bot iniciado...")
    app.run_polling()


if __name__ == "__main__":
    main()