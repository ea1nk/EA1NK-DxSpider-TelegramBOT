# Como crear un bot de Telegram con BotFather

Guia sencilla para crear tu bot en pocos minutos.

## 1. Abrir BotFather
1. Abre Telegram.
2. Busca **BotFather** (cuenta oficial con verificacion).
3. Inicia el chat.

## 2. Crear un bot nuevo
1. Envia este comando:
   `/newbot`
2. BotFather te pedira:
   - **Nombre del bot** (el que veran los usuarios)
   - **Username** (debe terminar en `bot`, por ejemplo: `mi_dx_bot`)

## 3. Guardar el token
Al crear el bot, BotFather te entrega un **token HTTP API**.

- Guardalo en un lugar seguro.
- No lo compartas en publico.
- Si se filtra, regeneralo desde BotFather (`/revoke` o reset de token).

## 4. Probar el bot
1. Abre el enlace de tu bot que te da BotFather.
2. Pulsa **Start** o envia `/start`.
3. Si tu aplicacion esta corriendo, el bot deberia responder.

## 5. Ajustes utiles en BotFather
Comandos recomendados:
- `/setdescription` -> Descripcion larga.
- `/setabouttext` -> Texto corto de perfil.
- `/setuserpic` -> Foto del bot.
- `/setcommands` -> Comandos del menu (ejemplo: `start`, `help`).

## 6. Anadir bot a un grupo (opcional)
1. Anade tu bot al grupo.
2. Si quieres que lea todos los mensajes, desactiva privacidad:
   - En BotFather: `/setprivacy`
   - Selecciona tu bot
   - Elige **Disable**

## 7. Seguridad basica
- Guarda el token en variables de entorno (por ejemplo `.env`).
- No subas tokens a repositorios publicos.
- Cambia el token si sospechas que se expuso.

## 8. Configuracion rapida para este proyecto
Este repositorio usa estas variables de entorno:

- `BOT_TOKEN` (obligatoria): token de Telegram generado con BotFather.
- `SPIDER_HOST` (opcional): host de DXSpider. Por defecto `dxspider`.
- `SPIDER_PORT` (opcional): puerto de DXSpider. Por defecto `23`.
- `MY_CALL` (opcional): indicativo usado por el bot. Por defecto `BOT`.
- `HTTPS_PROXY` (opcional): proxy si tu red lo necesita.

Ejemplo:

```bash
export BOT_TOKEN="tu_token_de_telegram"
export SPIDER_HOST="dxspider"
export SPIDER_PORT="23"
export MY_CALL="BOT"
python main.py
```

---
Listo. Tu bot de Telegram ya esta creado y preparado para conectarlo a tu codigo.
