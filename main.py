import asyncio, os, re, time
from collections import deque
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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
        self.debug_telnet = os.getenv("DEBUG_TELNET", "0").lower() in ("1", "true", "yes", "on")
        self.db = DatabaseManager()
        
        # Configuración de la App (con bypass de proxy si las variables están vacías)
        self.app = (
            Application.builder()
            .token(self.token)
            .get_updates_request(HTTPXRequest(proxy_url=os.getenv("HTTPS_PROXY") or None))
            .request(HTTPXRequest(proxy_url=os.getenv("HTTPS_PROXY") or None))
            .build()
        )

    @staticmethod
    def _get_lang(update):
        user = update.effective_user
        return getattr(user, "language_code", None) or "en"

    @staticmethod
    async def _reply(update, text, parse_mode=None):
        # Some update types don't populate update.message.
        msg = update.effective_message
        if msg:
            await msg.reply_text(text, parse_mode=parse_mode)

    async def handle_error(self, update, context):
        print(f"[ERROR] Handler: {context.error}")

    def _dbg(self, msg):
        if self.debug_telnet:
            print(f"[DEBUG][TELNET] {msg}")

    @staticmethod
    def _parse_spot(msg):
        legacy = re.search(r"DX de ([\w-]+):\s+(\d+\.\d+)\s+([\w/]+)\s+(.*)", msg)
        if legacy:
            return legacy.group(1), legacy.group(2), legacy.group(3), legacy.group(4)

        if msg.startswith("PC11^"):
            parts = msg.split("^")
            if len(parts) >= 7:
                freq = parts[1].strip()
                dx_call = parts[2].strip()
                comment = parts[5].strip()
                spotter = parts[6].strip()
                if freq and dx_call:
                    return spotter, freq, dx_call, comment

        return None

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
                self._dbg(f"Intentando conexion a {self.host}:{self.port}...")
                reader, writer = await asyncio.open_connection(self.host, self.port)
                peer = writer.get_extra_info("peername")
                local = writer.get_extra_info("sockname")
                self._dbg(f"Conexion TCP establecida. local={local} remote={peer}")
                self._dbg("Esperando banner/prompt de login del cluster...")

                login_sent = False
                banner_buffer = ""
                login_buffer = ""
                while not login_sent:
                    try:
                        chunk = await asyncio.wait_for(reader.read(1), timeout=30.0)
                    except asyncio.TimeoutError:
                        raise TimeoutError("Timeout esperando prompt 'login:' del cluster")

                    if not chunk:
                        raise ConnectionError("Conexion cerrada antes del login")

                    text = chunk.decode('utf-8', errors='ignore')
                    banner_buffer += text
                    login_buffer = (login_buffer + text)[-64:]

                    while "\n" in banner_buffer:
                        line, banner_buffer = banner_buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._dbg(f"Banner: {line}")

                    if "login:" in login_buffer.lower():
                        writer.write(f"{self.call}\n".encode())
                        await writer.drain()
                        self._dbg(f"Prompt 'login:' detectado. Login enviado con indicativo '{self.call}'")
                        login_sent = True

                print(f"[INFO] Conectado a DXSpider en {self.host}")
                first_line_logged = False
                while True:
                    line = await reader.readline()
                    if not line:
                        self._dbg("Conexion cerrada por el servidor remoto.")
                        break
                    msg = line.decode('utf-8', errors='ignore').strip()
                    if self.debug_telnet and not first_line_logged and msg:
                        self._dbg(f"Primer mensaje recibido: {msg}")
                        first_line_logged = True
                    parsed_spot = self._parse_spot(msg)
                    if parsed_spot:
                        spotter, freq, dx_call, comment = parsed_spot
                        band = obtener_banda(float(freq))
                        mode = detectar_modo_definitivo(freq, comment)
                        is_rbn = "-#" in spotter or "SKIMMER" in comment.upper()

                        self._dbg(f"Spot detectado: dx={dx_call} freq={freq} band={band} mode={mode} spotter={spotter}")
                        
                        if not self.es_duplicado(dx_call, freq, mode):
                            users = self.db.find_interested_users(dx_call, band, mode, is_rbn)
                            self._dbg(f"Usuarios coincidentes para {dx_call}: {len(users)}")
                            for uid, lang in users:
                                txt = get_text('spot', lang, call=dx_call, band=band, mode=mode, freq=freq, comment=comment)
                                await self.app.bot.send_message(chat_id=uid, text=txt, parse_mode='HTML')
            except Exception as e:
                print(f"[ERROR] Telnet: {e}")
                self._dbg("Reintentando conexion en 15 segundos...")
                await asyncio.sleep(15)

    async def handle_start(self, update, context):
        lang = self._get_lang(update)
        name = getattr(update.effective_user, "first_name", "") or ""
        await self._reply(update, get_text('start', lang, name=name), parse_mode='HTML')

    async def handle_help(self, update, context):
        lang = self._get_lang(update)
        await self._reply(update, get_text('help', lang), parse_mode='HTML')

    @staticmethod
    def _validate_bands(band_str):
        """Validate and normalize band list. Returns (valid, normalized_string)"""
        # Check for wildcard/ALL
        if band_str.strip().lower() in ("all", "*"):
            return True, "all"
        
        valid_bands = {"160", "80", "60", "40", "30", "20", "17", "15", "12", "10", "6", "4", "2", "uhf"}
        bands = [b.strip().lower() for b in band_str.split(",") if b.strip()]
        invalid = [b for b in bands if b not in valid_bands]
        if invalid:
            return False, None
        return True, ",".join(bands).lower()

    @staticmethod
    def _validate_modes(mode_str):
        """Validate and normalize mode list. Returns (valid, normalized_string)"""
        # Check for wildcard/ALL
        if mode_str.strip().upper() in ("ALL", "*"):
            return True, "ALL"
        
        valid_modes = {"ssb", "cw", "digi", "ft8"}
        modes = [m.strip().upper() for m in mode_str.split(",") if m.strip()]
        invalid = [m for m in modes if m.lower() not in valid_modes]
        if invalid:
            return False, None
        return True, ",".join(m.upper() for m in modes)

    async def handle_setfilter(self, update, context):
        lang = self._get_lang(update)
        
        if len(context.args) < 1 or len(context.args) > 3:
            return await self._reply(update, get_text('filter_error', lang), parse_mode='HTML')
        
        call = context.args[0].upper()
        
        if len(context.args) == 1:
            # /setfilter <CALL> => all bands, all modes
            bands, modes = "all", "ALL"
        
        elif len(context.args) == 2:
            # /setfilter <CALL> <bands_or_modes>
            second = context.args[1]
            if second == "*":
                return await self._reply(update, get_text('filter_error', lang), parse_mode='HTML')
            
            valid, normalized = self._validate_bands(second)
            if valid:
                # Second arg is bands
                bands, modes = normalized, "ALL"
            else:
                # Try as modes
                valid, normalized = self._validate_modes(second)
                if valid:
                    bands, modes = "all", normalized
                else:
                    return await self._reply(update, get_text('invalid_bands', lang), parse_mode='HTML')
        
        elif len(context.args) == 3:
            # /setfilter <CALL> <bands> <modes>
            second = context.args[1]
            third = context.args[2]
            
            if second == "*":
                # /setfilter <CALL> * <modes>
                bands = "all"
                valid, normalized = self._validate_modes(third)
                if not valid:
                    return await self._reply(update, get_text('invalid_modes', lang), parse_mode='HTML')
                modes = normalized
            else:
                # /setfilter <CALL> <bands> <modes>
                valid, normalized_bands = self._validate_bands(second)
                if not valid:
                    return await self._reply(update, get_text('invalid_bands', lang), parse_mode='HTML')
                
                valid, normalized_modes = self._validate_modes(third)
                if not valid:
                    return await self._reply(update, get_text('invalid_modes', lang), parse_mode='HTML')
                
                bands, modes = normalized_bands, normalized_modes
        
        self.db.add_filter(update.effective_user.id, call, bands, modes, lang)
        await self._reply(update, get_text('filter_saved', lang, call=call, bands=bands, mode=modes))

    async def handle_myfilters(self, update, context):
        filters = self.db.get_user_filters(update.effective_user.id)
        if not filters:
            return await self._reply(update, "<i>No tienes filtros activos.</i>", parse_mode='HTML')
        
        txt = "<b>📋 Tus Alertas:</b>\n\n"
        keyboard = []
        
        for f in filters:
            # f[0]=id, f[1]=call, f[2]=bandas, f[3]=modos, f[4]=rbn_enabled
            filter_id, call, bands, modes, rbn_enabled = f[0], f[1], f[2], f[3], f[4] if len(f) > 4 else 1
            rbn_icon = "✅" if rbn_enabled == 1 else "❌"
            
            # Mostrar el filtro en el texto
            txt += f"🔹 <b>{call}</b> | B: {bands} | M: {modes} | RBN: {rbn_icon}\n"
            
            # Añadir botón de eliminar
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Borrar {call}",
                    callback_data=f"delete_filter:{filter_id}"
                )
            ])
        
        keyboard_markup = InlineKeyboardMarkup(keyboard)
        msg = update.effective_message
        if msg:
            await msg.reply_text(txt, parse_mode='HTML', reply_markup=keyboard_markup)

    async def handle_delete_filter_button(self, update, context):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if not data.startswith("delete_filter:"):
            return
        
        try:
            filter_id = int(data.split(":")[1])
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Error al procesar la solicitud.")
            return
        
        success = self.db.delete_filter(update.effective_user.id, str(filter_id))
        
        if success:
            await query.edit_message_text("✅ Filtro eliminado correctamente.")
        else:
            await query.edit_message_text("❌ No se pudo eliminar el filtro (ID no válido).")



    async def handle_last(self, update, context):
        lang = self._get_lang(update)
        if not context.args: return await self._reply(update, "Usa: /last [Call]")
        call = context.args[0].upper()
        recientes = self.db.get_recent_spots(call)
        if recientes:
            for s in recientes:
                b_s = obtener_banda(float(s['freq']))
                m_s = detectar_modo_definitivo(s['freq'], s['comment'])
                txt = get_text('spot', lang, call=s['dxcall'], band=b_s, mode=m_s, freq=s['freq'], comment=s['comment'])
                await self._reply(update, txt, parse_mode='HTML')
        else:
            await self._reply(update, get_text('no_recent', lang, call=call), parse_mode='HTML')

    async def handle_rbn(self, update, context):
        lang = self._get_lang(update)
        if not context.args or context.args[0].lower() not in ["on", "off"]:
            return await self._reply(update, "Usa: /rbn on | off")
        status = context.args[0].lower()
        self.db.update_rbn_preference(update.effective_user.id, status)
        await self._reply(update, get_text('rbn_status', lang, status=status.upper()), parse_mode='HTML')

    async def run(self):
        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(CommandHandler("help", self.handle_help))
        self.app.add_handler(CommandHandler("setfilter", self.handle_setfilter))
        self.app.add_handler(CommandHandler("myfilters", self.handle_myfilters))
        self.app.add_handler(CommandHandler("last", self.handle_last))
        self.app.add_handler(CommandHandler("rbn", self.handle_rbn))
        self.app.add_handler(CallbackQueryHandler(self.handle_delete_filter_button))
        self.app.add_error_handler(self.handle_error)
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        print("[INFO] Bot de Telegram iniciado.")
        await self.handle_telnet()

if __name__ == "__main__":
    asyncio.run(DXBot().run())