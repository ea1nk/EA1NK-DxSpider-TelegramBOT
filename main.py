import asyncio, os, re, time, signal
from collections import deque
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Conflict, TimedOut, NetworkError, RetryAfter, TelegramError
from database import DatabaseManager
from logic import obtener_banda, detectar_modo_definitivo
from localestr import get_text
from telegram.request import HTTPXRequest

# Caché de duplicados: (huella, timestamp)
CACHE_DUPLICADOS = deque(maxlen=500)
TIEMPO_EXPIRACION = 600 # 10 minutos
CLEARALL_CONFIRM_TIMEOUT = 300  # 5 minutos

class DXBot:
    CALL_RE = re.compile(r"^[A-Z0-9][A-Z0-9/.-]{2,}$")
    RBN_MARKER_RE = re.compile(r"\b(?:RBN|SK[0-9I]MMR|SKIMMER|CWSKIMMER|CW\s+SKIMMER)\b", re.IGNORECASE)
    RBN_ON_BY_RE = re.compile(
        r"\b(?P<dx>[A-Z0-9/.-]+)\s+on\s+(?P<freq>\d+(?:\.\d+)?)\s+by\s+(?P<spotter>[A-Z0-9/.-]+)\b",
        re.IGNORECASE,
    )
    RBN_KEY_RE = re.compile(r"RBN:\s*SPOT\s*key:\s*'(?P<dx>[^|']+)\|(?P<freq>\d+)'", re.IGNORECASE)
    TIME_RE = re.compile(r"\b(?P<time>\d{4}Z)\b", re.IGNORECASE)
    RBN_PROGRESS_RE = re.compile(
        r"RBN:\s+SPOT\s+key:\s*'(?P<dx_key>[^|']+)\|(?P<freq_key>\d+)'"
        r"(?:\s*=\s*(?P<dx_eq>[A-Z0-9/.-]+)\s+on\s+(?P<freq_eq>[\d.]+)\s+by\s+(?P<spotter>[A-Z0-9/.-]+))?",
        re.IGNORECASE,
    )

    def __init__(self):
        self.token = os.getenv("BOT_TOKEN")
        self.host = os.getenv("SPIDER_HOST", "dxspider")
        self.port = int(os.getenv("SPIDER_PORT", 23))
        self.call = os.getenv("MY_CALL", "BOT")
        self.debug_telnet = os.getenv("DEBUG_TELNET", "0").lower() in ("1", "true", "yes", "on")
        self.db = DatabaseManager()
        self.shutdown_event = asyncio.Event()
        # user_id -> expiry timestamp. While present, spot delivery is paused for that user.
        self.pending_clear_confirmations = {}
        self.http_pool_size = int(os.getenv("TG_POOL_SIZE", "20"))
        self.http_pool_timeout = float(os.getenv("TG_POOL_TIMEOUT", "10"))
        self.send_queue_max_size = int(os.getenv("TG_SEND_QUEUE_MAX", "5000"))
        self.queue_enqueue_timeout = float(os.getenv("TG_ENQUEUE_TIMEOUT", "0.3"))
        self.queue_drain_timeout = float(os.getenv("TG_DRAIN_TIMEOUT", "15"))
        self.min_sender_workers = max(1, int(os.getenv("TG_MIN_SENDER_WORKERS", str(max(2, self.http_pool_size // 2)))))
        self.max_sender_workers = max(self.min_sender_workers, int(os.getenv("TG_MAX_SENDER_WORKERS", str(min(64, self.http_pool_size * 4)))))
        self.scale_up_every = max(1, int(os.getenv("TG_SCALE_UP_EVERY", "50")))
        self.sender_queue = asyncio.Queue(maxsize=self.send_queue_max_size)
        self.sender_workers = []
        self.sender_scaler_task = None
        self.dropped_messages = 0
        self.send_failures = 0
        
        # Configuración de la App (con bypass de proxy si las variables están vacías)
        request_kwargs = {
            "proxy_url": os.getenv("HTTPS_PROXY") or None,
            "connection_pool_size": self.http_pool_size,
            "pool_timeout": self.http_pool_timeout,
        }
        self.app = (
            Application.builder()
            .token(self.token)
            .get_updates_request(HTTPXRequest(**request_kwargs))
            .request(HTTPXRequest(**request_kwargs))
            .build()
        )

    def _target_sender_workers(self):
        qsize = self.sender_queue.qsize()
        dynamic_workers = (qsize // self.scale_up_every) + 1
        dynamic_workers = max(self.min_sender_workers, dynamic_workers)
        return min(self.max_sender_workers, dynamic_workers)

    def _spawn_sender_worker(self):
        worker_id = len(self.sender_workers) + 1
        task = asyncio.create_task(self._sender_worker(worker_id), name=f"tg-sender-{worker_id}")
        self.sender_workers.append(task)

    async def _start_sender_pool(self):
        for _ in range(self.min_sender_workers):
            self._spawn_sender_worker()
        self.sender_scaler_task = asyncio.create_task(self._sender_scaler(), name="tg-sender-scaler")
        print(
            f"[INFO] Pool Telegram iniciado: workers={self.min_sender_workers}-{self.max_sender_workers}, "
            f"queue_max={self.send_queue_max_size}, pool_size={self.http_pool_size}"
        )

    async def _stop_sender_pool(self):
        try:
            await asyncio.wait_for(self.sender_queue.join(), timeout=self.queue_drain_timeout)
        except asyncio.TimeoutError:
            pending = self.sender_queue.qsize()
            print(f"[WARN] Timeout drenando cola Telegram ({pending} pendientes)")

        if self.sender_scaler_task:
            self.sender_scaler_task.cancel()
            try:
                await self.sender_scaler_task
            except asyncio.CancelledError:
                pass
            self.sender_scaler_task = None

        workers = list(self.sender_workers)
        for task in workers:
            task.cancel()
        for task in workers:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.sender_workers.clear()

    async def _sender_scaler(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(1.0)
            target = self._target_sender_workers()
            current = len(self.sender_workers)
            if target > current:
                for _ in range(target - current):
                    self._spawn_sender_worker()
                self._dbg(f"Escalado Telegram workers: {current} -> {len(self.sender_workers)}")

    async def _enqueue_telegram(self, chat_id, text):
        if self.shutdown_event.is_set():
            return False
        try:
            await asyncio.wait_for(self.sender_queue.put((chat_id, text)), timeout=self.queue_enqueue_timeout)
            return True
        except asyncio.TimeoutError:
            self.dropped_messages += 1
            if self.dropped_messages == 1 or self.dropped_messages % 50 == 0:
                print(
                    f"[WARN] Cola Telegram saturada. Mensajes descartados={self.dropped_messages} "
                    f"qsize={self.sender_queue.qsize()}/{self.send_queue_max_size}"
                )
            return False

    async def _send_telegram_with_retry(self, chat_id, text):
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                await self.app.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
                return True
            except RetryAfter as err:
                wait_seconds = float(getattr(err, "retry_after", 1.0) or 1.0)
                await asyncio.sleep(min(wait_seconds, 10.0))
            except (TimedOut, NetworkError):
                if attempt < max_attempts:
                    await asyncio.sleep(min(2 ** (attempt - 1), 4))
                else:
                    self.send_failures += 1
                    if self.send_failures == 1 or self.send_failures % 50 == 0:
                        print(f"[ERROR] Fallos Telegram acumulados={self.send_failures}")
                    return False
            except TelegramError as err:
                self.send_failures += 1
                print(f"[ERROR] Telegram send (uid={chat_id}): {err}")
                return False
            except Exception as err:
                self.send_failures += 1
                print(f"[ERROR] Telegram send inesperado (uid={chat_id}): {err}")
                return False
        return False

    async def _sender_worker(self, worker_id):
        current_task = asyncio.current_task()
        try:
            while True:
                if self.shutdown_event.is_set() and self.sender_queue.empty():
                    break
                try:
                    uid, txt = await asyncio.wait_for(self.sender_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    target = self._target_sender_workers()
                    if len(self.sender_workers) > target and len(self.sender_workers) > self.min_sender_workers:
                        break
                    continue

                try:
                    await self._send_telegram_with_retry(uid, txt)
                finally:
                    self.sender_queue.task_done()
        except asyncio.CancelledError:
            pass
        finally:
            if current_task in self.sender_workers:
                self.sender_workers.remove(current_task)
            self._dbg(f"Worker Telegram detenido: {worker_id}")

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
        if isinstance(context.error, Conflict):
            print(f"[ERROR] Conflict detectado: {context.error}")
            print("[ERROR] Otra instancia del bot está en ejecución. Deteniendo este proceso...")
            self.shutdown_event.set()
            return
        print(f"[ERROR] Handler: {context.error}")

    def _dbg(self, msg):
        if self.debug_telnet:
            print(f"[DEBUG][TELNET] {msg}")

    @staticmethod
    def _parse_spot(msg):
        legacy = re.search(r"DX de\s+([A-Z0-9/#.-]+):\s+(\d+(?:\.\d+)?)\s+([A-Z0-9/#.-]+)\s+(.*)", msg, re.IGNORECASE)
        if legacy:
            return legacy.group(1).upper(), legacy.group(2), legacy.group(3).upper(), legacy.group(4)

        if msg.startswith("PC11^"):
            parts = msg.split("^")
            if len(parts) >= 7:
                freq = parts[1].strip()
                dx_call = parts[2].strip()
                comment = parts[5].strip()
                spotter = parts[6].strip()
                if freq and dx_call:
                    return spotter, freq, dx_call, comment

        # PC61 = reemplazo de PC11 con IP extra (misma estructura de spot).
        if msg.startswith("PC61^"):
            parts = msg.split("^")
            if len(parts) >= 9:
                freq = parts[1].strip()
                dx_call = parts[2].strip()
                comment = parts[5].strip()
                spotter = parts[6].strip()
                if freq and dx_call:
                    return spotter, freq, dx_call, comment

        # PC26 = Merge DX info.
        if msg.startswith("PC26^"):
            parts = msg.split("^")
            if len(parts) >= 8:
                freq = parts[1].strip()
                dx_call = parts[2].strip()
                comment = parts[5].strip()
                spotter = parts[6].strip()
                if freq and dx_call:
                    return spotter, freq, dx_call, comment

        # Texto de progreso RBN (no PCxx), por ejemplo:
        # RBN: SPOT key: 'HF9T|210740' = HF9T on 21074 by K9LC ... route: SK1MMR ...
        rbn_match = DXBot.RBN_PROGRESS_RE.search(msg)
        if rbn_match:
            dx_call = (rbn_match.group("dx_eq") or rbn_match.group("dx_key") or "").strip().upper()
            spotter = (rbn_match.group("spotter") or "RBN").strip().upper()

            freq_eq = rbn_match.group("freq_eq")
            if freq_eq:
                freq = freq_eq.strip()
            else:
                # freq_key viene como kHz*10 (210740 => 21074.0)
                freq_key = rbn_match.group("freq_key")
                freq = str(float(freq_key) / 10.0)

            comment = msg.strip()
            if dx_call and freq:
                return spotter, freq, dx_call, comment

        return None

    @staticmethod
    def _has_rbn_marker(text):
        if not text:
            return False
        return "-#" in text or bool(DXBot.RBN_MARKER_RE.search(text))

    @staticmethod
    def _looks_like_rbn(msg):
        return DXBot._has_rbn_marker(msg)

    @staticmethod
    def _parse_rbn_fallback(msg):
        """Fallback parser for RBN-like text not matched by primary parsers."""
        on_by = DXBot.RBN_ON_BY_RE.search(msg)
        if on_by:
            dx_call = on_by.group("dx").strip().upper()
            freq = on_by.group("freq").strip()
            spotter = on_by.group("spotter").strip().upper()
            if dx_call and freq:
                return spotter, freq, dx_call, msg.strip()

        key_match = DXBot.RBN_KEY_RE.search(msg)
        if key_match:
            dx_call = key_match.group("dx").strip().upper()
            freq_key = key_match.group("freq").strip()
            if dx_call and freq_key:
                return "RBN", str(float(freq_key) / 10.0), dx_call, msg.strip()

        return None

    @staticmethod
    def _extract_time_and_clean_comment(msg, comment):
        """Extract spot time and remove duplicated time tokens from comment text."""
        spot_time = "N/A"

        if msg.startswith("PC11^") or msg.startswith("PC61^") or msg.startswith("PC26^"):
            parts = msg.split("^")
            if len(parts) >= 5 and parts[4].strip():
                spot_time = parts[4].strip().upper()

        if spot_time == "N/A":
            msg_times = DXBot.TIME_RE.findall(msg)
            if msg_times:
                spot_time = msg_times[-1].upper()

        clean_comment = (comment or "").strip()
        if spot_time != "N/A":
            clean_comment = re.sub(rf"\b{re.escape(spot_time)}\b", "", clean_comment, flags=re.IGNORECASE)
        clean_comment = re.sub(r"\s+\d{4}Z\s*$", "", clean_comment, flags=re.IGNORECASE)
        clean_comment = re.sub(r"@\s*\d{4}Z", "", clean_comment, flags=re.IGNORECASE)
        clean_comment = re.sub(r"\s{2,}", " ", clean_comment).strip()
        return spot_time, clean_comment

    @staticmethod
    def _build_origin_label(spotter, is_rbn):
        s = (spotter or "UNKNOWN").strip().upper()
        if is_rbn:
            s = re.sub(r"-#$", "", s)
            return f"RBN - {s}"
        return s

    def es_duplicado(self, dx_call, freq, modo):
        ahora = time.time()
        freq_r = round(float(freq) * 2) / 2
        huella = f"{dx_call}_{freq_r}_{modo}"
        for h, ts in list(CACHE_DUPLICADOS):
            if h == huella and (ahora - ts) < TIEMPO_EXPIRACION: return True
        CACHE_DUPLICADOS.append((huella, ahora))
        return False

    def _set_clear_pending(self, user_id):
        self.pending_clear_confirmations[user_id] = time.time() + CLEARALL_CONFIRM_TIMEOUT

    def _clear_pending(self, user_id):
        self.pending_clear_confirmations.pop(user_id, None)

    def _is_clear_pending(self, user_id):
        expiry = self.pending_clear_confirmations.get(user_id)
        if not expiry:
            return False
        if time.time() > expiry:
            self.pending_clear_confirmations.pop(user_id, None)
            return False
        return True

    async def handle_telnet(self):
        while not self.shutdown_event.is_set():
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
                while not login_sent and not self.shutdown_event.is_set():
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

                if self.shutdown_event.is_set():
                    writer.close()
                    await writer.wait_closed()
                    break

                print(f"[INFO] Conectado a DXSpider en {self.host}")
                await asyncio.sleep(2)
                self._dbg("Espera post-login completada (2s) antes de enviar comandos de sesion")
                writer.write(b"set/skim\n")
                await writer.drain()
                self._dbg("Comando enviado al cluster: set/skim")
                first_line_logged = False
                while not self.shutdown_event.is_set():
                    line = await reader.readline()
                    if not line:
                        self._dbg("Conexion cerrada por el servidor remoto.")
                        break
                    msg = line.decode('utf-8', errors='ignore').strip()
                    if self.debug_telnet and not first_line_logged and msg:
                        self._dbg(f"Primer mensaje recibido: {msg}")
                        first_line_logged = True

                    is_supported_pc_spot = msg.startswith("PC11^") or msg.startswith("PC61^") or msg.startswith("PC26^")
                    if self.debug_telnet and msg.startswith("PC") and not is_supported_pc_spot:
                        self._dbg(f"Mensaje PC no-PC11 recibido (sin parser dedicado): {msg}")

                    parsed_spot = self._parse_spot(msg)
                    used_rbn_fallback = False
                    if not parsed_spot and self._looks_like_rbn(msg):
                        parsed_spot = self._parse_rbn_fallback(msg)
                        if parsed_spot:
                            used_rbn_fallback = True
                            self._dbg(f"Fallback RBN parseado: {msg}")
                        elif self.debug_telnet:
                            self._dbg(f"Posible RBN no parseado: {msg}")

                    if parsed_spot:
                        if self.debug_telnet:
                            if msg.startswith("PC11^"):
                                raw_format = "PC11"
                            elif msg.startswith("PC61^"):
                                raw_format = "PC61"
                            elif msg.startswith("PC26^"):
                                raw_format = "PC26"
                            elif "RBN: SPOT key:" in msg.upper():
                                raw_format = "RBN-TEXT"
                            elif used_rbn_fallback:
                                raw_format = "RBN-FALLBACK"
                            elif msg.startswith("DX de "):
                                raw_format = "LEGACY"
                            else:
                                raw_format = "UNKNOWN"
                            self._dbg(f"Raw spot parseado [{raw_format}]: {msg}")

                        spotter, freq, dx_call, comment = parsed_spot
                        band = obtener_banda(float(freq))
                        mode = detectar_modo_definitivo(freq, comment)
                        is_rbn = (
                            self._has_rbn_marker(spotter)
                            or self._has_rbn_marker(comment)
                            or self._has_rbn_marker(msg)
                        )
                        spot_time, clean_comment = self._extract_time_and_clean_comment(msg, comment)
                        origin = self._build_origin_label(spotter, is_rbn)

                        self._dbg(f"Spot detectado: dx={dx_call} freq={freq} band={band} mode={mode} spotter={spotter}")
                        
                        if not self.es_duplicado(dx_call, freq, mode):
                            users = self.db.find_interested_users(dx_call, band, mode, is_rbn)
                            self._dbg(f"Usuarios coincidentes para {dx_call}: {len(users)}")
                            for uid, lang in users:
                                if self._is_clear_pending(uid):
                                    continue
                                rbn_label = " <b>[RBN]</b>" if is_rbn else ""
                                txt = get_text('spot', lang, call=dx_call, band=band, mode=mode, freq=freq, comment=clean_comment, rbn_label=rbn_label, time=spot_time, origin=origin)
                                await self._enqueue_telegram(uid, txt)
                
                writer.close()
                await writer.wait_closed()
            
            except ConnectionError as e:
                print(f"[ERROR] Conexion a DXSpider perdida: {e}")
                print("[INFO] Reconectando en 10 segundos...")
                await asyncio.sleep(10)
            except TimeoutError as e:
                print(f"[ERROR] {e}")
                print("[INFO] Reconectando en 10 segundos...")
                await asyncio.sleep(10)
            except Exception as e:
                print(f"[ERROR] Telnet: {e}")
                self._dbg("Reintentando conexion en 15 segundos...")
                await asyncio.sleep(15)

    async def handle_start(self, update, context):
        lang = self._get_lang(update)
        name = getattr(update.effective_user, "first_name", "") or ""
        is_first_connection = self.db.register_user_if_new(update.effective_user.id)
        await self._reply(update, get_text('start', lang, name=name), parse_mode='HTML')
        if is_first_connection:
            await self._reply(update, get_text('help', lang), parse_mode='HTML')

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
        if data == "clear_all_confirm":
            lang = self._get_lang(update)
            user_id = update.effective_user.id
            if not self._is_clear_pending(user_id):
                await query.edit_message_text(get_text('clearall_expired', lang), parse_mode='HTML')
                return

            deleted = self.db.delete_all_filters(user_id)
            self._clear_pending(user_id)
            if deleted > 0:
                await query.edit_message_text(get_text('filters_cleared', lang, count=deleted), parse_mode='HTML')
            else:
                await query.edit_message_text(get_text('no_filters_to_clear', lang), parse_mode='HTML')
            return

        if data == "clear_all_cancel":
            lang = self._get_lang(update)
            user_id = update.effective_user.id
            self._clear_pending(user_id)
            await query.edit_message_text(get_text('clearall_cancelled', lang), parse_mode='HTML')
            return

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
                spot_time = "N/A"
                if s.get('time'):
                    spot_time = time.strftime("%H%MZ", time.gmtime(int(s['time'])))
                txt = get_text('spot', lang, call=s['dxcall'], band=b_s, mode=m_s, freq=s['freq'], comment=s['comment'], rbn_label="", time=spot_time, origin="N/A")
                await self._reply(update, txt, parse_mode='HTML')
        else:
            await self._reply(update, get_text('no_recent', lang, call=call), parse_mode='HTML')

    async def handle_clearallfilters(self, update, context):
        lang = self._get_lang(update)
        user_id = update.effective_user.id
        self._set_clear_pending(user_id)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(get_text('clearall_confirm_yes', lang), callback_data="clear_all_confirm"),
                InlineKeyboardButton(get_text('clearall_confirm_no', lang), callback_data="clear_all_cancel"),
            ]
        ])
        msg = update.effective_message
        if msg:
            await msg.reply_text(get_text('clearall_confirm_prompt', lang), parse_mode='HTML', reply_markup=keyboard)

    async def handle_rbn(self, update, context):
        lang = self._get_lang(update)
        if not context.args or context.args[0].lower() not in ["on", "off"]:
            return await self._reply(update, "Usa: /rbn on | off")
        status = context.args[0].lower()
        self.db.update_rbn_preference(update.effective_user.id, status)
        await self._reply(update, get_text('rbn_status', lang, status=status.upper()), parse_mode='HTML')

    async def handle_about(self, update, context):
        lang = self._get_lang(update)
        await self._reply(update, get_text('about', lang), parse_mode='HTML')

    async def run(self):
        # Registrar handlers para graceful shutdown
        loop = asyncio.get_event_loop()
        
        def signal_handler(signum, frame):
            print(f"[INFO] Señal {signal.Signals(signum).name} recibida. Iniciando shutdown graceful...")
            self.shutdown_event.set()
        
        loop.add_signal_handler(signal.SIGTERM, signal_handler, signal.SIGTERM, None)
        loop.add_signal_handler(signal.SIGINT, signal_handler, signal.SIGINT, None)
        
        # Registrar handlers de comandos
        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(CommandHandler("help", self.handle_help))
        self.app.add_handler(CommandHandler("setfilter", self.handle_setfilter))
        self.app.add_handler(CommandHandler("myfilters", self.handle_myfilters))
        self.app.add_handler(CommandHandler("clearallfilters", self.handle_clearallfilters))
        self.app.add_handler(CommandHandler("last", self.handle_last))
        self.app.add_handler(CommandHandler("rbn", self.handle_rbn))
        self.app.add_handler(CommandHandler("about", self.handle_about))
        self.app.add_handler(CallbackQueryHandler(self.handle_delete_filter_button))
        self.app.add_error_handler(self.handle_error)
        
        await self.app.initialize()
        await self.app.start()
        await self._start_sender_pool()
        await self.app.updater.start_polling()
        print("[INFO] Bot de Telegram iniciado.")
        
        # Ejecutar telnet handler y esperar shutdown
        try:
            await asyncio.gather(
                self.handle_telnet(),
                self.shutdown_event.wait()
            )
        except asyncio.CancelledError:
            print("[INFO] Bot cancelado.")
        finally:
            print("[INFO] Deteniendo bot de Telegram...")
            await self._stop_sender_pool()
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            print("[INFO] Bot detenido correctamente.")

if __name__ == "__main__":
    asyncio.run(DXBot().run())