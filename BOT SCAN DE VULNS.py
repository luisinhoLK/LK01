import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler
)
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import concurrent.futures

# Configuração do logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações Otimizadas
MAX_SUBDOMAINS = 5  # Reduzido para maior velocidade
MAX_LINKS = 10      # Menos links para verificação rápida
MAX_WORKERS = 10    # Aumentado para paralelismo máximo

def validate_target(url):
    """Validação rápida de URL"""
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = f'http://{url}'
            parsed = urlparse(url)
        
        if any(n in parsed.netloc for n in ['localhost', '127.0.0.1']):
            return False, "Scan local bloqueado"
            
        return True, url
    except:
        return False, "URL inválida"

def fast_scan(target_url):
    """Varredura otimizada com tempo limite"""
    session = requests.Session()
    vulns = []
    
    # Testes rápidos (exemplo simplificado)
    try:
        # SQLi Test
        r = session.get(target_url + "'", timeout=3)
        if "sql" in r.text.lower():
            vulns.append("Possível SQLi")
            
        # XSS Test
        r = session.get(target_url + "?test=<script>", timeout=3)
        if "<script>" in r.text:
            vulns.append("Possível XSS")
            
        # SSRF Test
        r = session.get(target_url + "?url=http://localhost", timeout=3)
        if "localhost" in r.text:
            vulns.append("Possível SSRF")
            
    except Exception as e:
        logger.error(f"Erro rápido: {str(e)}")
    
    return {target_url: vulns}

# Handlers do Telegram
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_markdown_v2(
        f"👋 Olá {user.mention_markdown_v2()}\! Envie uma URL para verificar vulnerabilidades"
    )

def handle_url(update: Update, context: CallbackContext) -> None:
    """Confirmação antes do scan"""
    url = update.message.text
    valid, msg = validate_target(url)
    
    if not valid:
        update.message.reply_text(f"❌ {msg}")
        return
    
    keyboard = [[InlineKeyboardButton("✅ Sim, verificar agora", callback_data=f"scan_{url}")]]
    
    update.message.reply_text(
        f"🔍 Quer verificar possíveis vulnerabilidades deste site?\n{url}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def start_scan(update: Update, context: CallbackContext) -> None:
    """Executa o scan rápido"""
    query = update.callback_query
    query.answer()
    
    url = query.data.split("scan_")[1]
    query.edit_message_text("⚡ Varredura rápida em andamento...")
    
    try:
        results = fast_scan(url)
        vulns = results.get(url, [])
        
        if vulns:
            response = f"🚨 *Resultados para {url}*\n\n" + "\n".join(f"• {v}" for v in vulns)
        else:
            response = f"✅ Nenhuma vulnerabilidade óbvia encontrada em {url}"
            
        query.edit_message_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        query.edit_message_text("❌ Falha na verificação rápida")

def main():
    updater = Updater("7565269150:AAGsvZz0nYFoWZW5nj64MvuBwX0czNoR3DM")
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(start_scan, pattern=r"^scan_"))
    
    dispatcher.add_handler(MessageHandler(
        Filters.regex(r'^https?://\S+$') & ~Filters.command,
        handle_url,
        run_async=True
    ))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    
    
