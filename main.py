import asyncio, os, re, time
from collections import deque
from telegram.ext import Application, CommandHandler
from database import DatabaseManager
from logic import obtener_banda, detectar_modo_definitivo
from localestr import get_text
from telegram.request import HTTPXRequest

# Caché de duplicados: (huella, timestamp)
CACHE_DUPLICADOS = deque(maxlen=500)
TIEMPO_EXPIRACION = 600 # 10 minutos

class DXBot:
    def __init__(self):
        self.token = os.getenv("BOT_TOKEN")
        self.host = os.getenv("SPIDER_HOST", "dxspider")
        self.port = int(os.getenv("SPIDER_PORT", 23))
        self.call = os.getenv("MY_CALL", "BOT")
        self.db = DatabaseManager()
        
        # Configuración de la App (con bypass de proxy si las variables están vacías)
        self.app = (
            Application.builder()
            .token(self.token)
            .get_updates_request(HTTPXRequest(proxy_url=os.getenv("HTTPS_PROXY") or None))
            .request(HTTPXRequest(proxy_url=os.getenv("HTTPS_PROXY") or None))
            .build()
        )

    def es_duplicado(self, dx_call, freq, modo):
        ahora = time.time()
        freq_r = round(float(freq) * 2) / 2
        huella = f"{dx_call}_{freq_r}_{modo}"
        for h, ts in list(CACHE_DUPLICADOS):
            if h == huella and (ahora - ts) < TIEMPO_EXPIRACION: return True
        CACHE_DUPLICADOS.append((huella, ahora))
        return False

    async def handle_telnet(self):
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                writer.write(f"{self.call}\n".encode())
                await writer.drain()
                print(f"[INFO] Conectado a DXSpider en {self.host}")
                while True:
                    line = await reader.readline()
                    if not line: break
                    msg = line.decode('utf-8', errors='ignore').strip()
                    m = re.search(r"DX de ([\w-]+):\s+(\d+\.\d+)\s+([\w/]+)\s+(.*)", msg)
                    if m:
                        spotter, freq, dx_call, comment = m.group(1), m.group(2), m.group(3), m.group(4)
                        band = obtener_banda(float(freq))
                        mode = detectar_modo_definitivo(freq, comment)
                        is_rbn = "-#" in spotter or "SKIMMER" in comment.upper()
                        
                        if not self.es_duplicado(dx_call, freq, mode):
                            users = self.db.find_interested_users(dx_call, band, mode, is_rbn)
                            for uid, lang in users:
                                txt = get_text('spot', lang, call=dx_call, band=band, mode=mode, freq=freq, comment=comment)
                                await self.app.bot.send_message(chat_id=uid, text=txt, parse_mode='HTML')
            except Exception as e:
                print(f"[ERROR] Telnet: {e}")
                await asyncio.sleep(15)

    async def handle_start(self, update, context):
        lang = update.effective_user.language_code
        await update.message.reply_text(get_text('start', lang, name=update.effective_user.first_name), parse_mode='HTML')

    async def handle_help(self, update, context):
        lang = update.effective_user.language_code
        await update.message.reply_text(get_text('help', lang), parse_mode='HTML')

    async def handle_setfilter(self, update, context):
        lang = update.effective_user.language_code
        if len(context.args) < 3: 
            return await update.message.reply_text(get_text('help', lang), parse_mode='HTML')
        
        call, bands, mode = context.args[0].upper(), context.args[1].lower(), context.args[2].upper()
        self.db.add_filter(update.effective_user.id, call, bands, mode, lang)
        await update.message.reply_text(get_text('filter_saved', lang, call=call, bands=bands, mode=mode))

    async def handle_myfilters(self, update, context):
        filters = self.db.get_user_filters(update.effective_user.id)
        if not filters:
            return await update.message.reply_text("<i>No tienes filtros activos.</i>", parse_mode='HTML')
        
        txt = "<b>📋 Tus Alertas:</b>\n\n"
        for f in filters:
            # f[0]=id, f[1]=call, f[2]=bandas, f[3]=modos, f[4]=rbn_enabled
            rbn_icon = "✅" if (len(f) > 4 and f[4] == 1) else "❌"
            txt += f"🔹 <b>ID:</b> <code>{f[0]}</code> | <b>DX:</b> {f[1]}\n"
            txt += f"   B: {f[2]} | M: {f[3]} | RBN: {rbn_icon}\n\n"
        await update.message.reply_text(txt, parse_mode='HTML')

    async def handle_delfilter(self, update, context):
        if not context.args:
            return await update.message.reply_text("Usa: /delfilter [ID]")
        success = self.db.delete_filter(update.effective_user.id, context.args[0])
        msg = "✅ Filtro eliminado." if success else "❌ ID no válido."
        await update.message.reply_text(msg)

    async def handle_last(self, update, context):
        lang = update.effective_user.language_code
        if not context.args: return await update.message.reply_text("Usa: /last [Call]")
        call = context.args[0].upper()
        recientes = self.db.get_recent_spots(call)
        if recientes:
            for s in recientes:
                b_s = obtener_banda(float(s['freq']))
                m_s = detectar_modo_definitivo(s['freq'], s['comment'])
                txt = get_text('spot', lang, call=s['dxcall'], band=b_s, mode=m_s, freq=s['freq'], comment=s['comment'])
                await update.message.reply_text(txt, parse_mode='HTML')
        else:
            await update.message.reply_text(get_text('no_recent', lang, call=call), parse_mode='HTML')

    async def handle_rbn(self, update, context):
        lang = update.effective_user.language_code
        if not context.args or context.args[0].lower() not in ["on", "off"]:
            return await update.message.reply_text("Usa: /rbn on | off")
        status = context.args[0].lower()
        self.db.update_rbn_preference(update.effective_user.id, status)
        await update.message.reply_text(get_text('rbn_status', lang, status=status.upper()), parse_mode='HTML')

    async def run(self):
        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(CommandHandler("help", self.handle_help))
        self.app.add_handler(CommandHandler("setfilter", self.handle_setfilter))
        self.app.add_handler(CommandHandler("myfilters", self.handle_myfilters))
        self.app.add_handler(CommandHandler("delfilter", self.handle_delfilter))
        self.app.add_handler(CommandHandler("last", self.handle_last))
        self.app.add_handler(CommandHandler("rbn", self.handle_rbn))
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        print("[INFO] Bot de Telegram iniciado.")
        await self.handle_telnet()

if __name__ == "__main__":
    asyncio.run(DXBot().run())