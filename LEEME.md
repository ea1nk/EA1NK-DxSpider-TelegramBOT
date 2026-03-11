```
███████╗ ██████╗ ██████╗     ██████╗ ███████╗██╗   ██╗██╗ ██████╗███████╗███████╗
██╔════╝██╔════╝██╔═══██╗    ██╔══██╗██╔════╝██║   ██║██║██╔════╝██╔════╝██╔════╝
███████╗██║     ██║   ██║    ██║  ██║█████╗  ██║   ██║██║██║     █████╗  ███████╗
╚════██║██║     ██║▄▄ ██║    ██║  ██║██╔══╝  ╚██╗ ██╔╝██║██║     ██╔══╝  ╚════██║
███████║╚██████╗╚██████╔╝    ██████╔╝███████╗ ╚████╔╝ ██║╚██████╗███████╗███████║
╚══════╝ ╚═════╝ ╚══▀▀═╝     ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝╚══════╝
                                                                                 
███████╗ █████╗  ██╗███╗   ██╗██╗  ██╗                                           
██╔════╝██╔══██╗███║████╗  ██║██║ ██╔╝                                           
█████╗  ███████║╚██║██╔██╗ ██║█████╔╝                                            
██╔══╝  ██╔══██║ ██║██║╚██╗██║██╔═██╗                                            
███████╗██║  ██║ ██║██║ ╚████║██║  ██╗           
2026 EA1NK-DxSpider-TelegramBOT
```
# :robot: EA1NK-DxSpider-TelegramBOT

Bot de Telegram para alertas DX desde un cluster DXSpider, con filtros por usuario, control de duplicados y opcion de filtrar spots de RBN.

Este repositorio esta pensado para ejecutarse en Docker y forma parte del proyecto EA1NK-Docker-DxSpider:
https://github.com/ea1nk/EA1NK-Docker-DxSpider

## Que hace

- Se conecta por telnet a un nodo DXSpider.
- Lee y procesa spots DX en tiempo real.
- Envia alertas de Telegram solo a usuarios interesados por indicativo, banda y modo.
- Guarda filtros de cada usuario en SQLite local.
- Permite activar o desactivar spots de RBN/Skimmer por usuario.
- Puede consultar spots recientes en MySQL para el comando /last.

## Estructura del proyecto

- main.py: Ejecucion del bot y comandos de Telegram.
- database.py: Almacenamiento de filtros en SQLite y consulta MySQL.
- logic.py: Deteccion de banda y modo.
- localestr.py: Textos del bot por idioma.
- Dockerfile: Imagen del contenedor.
- docker-compose.yml.sample: Ejemplo de configuracion para Docker Compose.

## Requisitos

- Python 3.10 o superior.
- Token de bot de Telegram (BotFather).
- Acceso a un host DXSpider.
- Opcional: acceso a base de datos MySQL del cluster (necesario para /last).

## Guias rapidas de BotFather

- English: [HOW_TO_TELEGRAM_BOT_EN,md](HOW_TO_TELEGRAM_BOT_EN,md)
- Espanol: [TELEGRAM_BOT_COMO.md](TELEGRAM_BOT_COMO.md)

Dependencias en requirements.txt:

- python-telegram-bot==21.0.1
- mysql-connector-python==8.3.0

## Variables de entorno

Obligatoria:

- BOT_TOKEN: Token del bot de Telegram.

Recomendadas:

- SPIDER_HOST: Host de DXSpider (por defecto: dxspider).
- SPIDER_PORT: Puerto de DXSpider (por defecto: 23).
- MY_CALL: Indicativo usado para entrar al cluster (por defecto: BOT).
- DEBUG_TELNET: Activar logs de depuracion telnet (por defecto: 0, poner 1 para debug).
- PYTHONUNBUFFERED: Salida sin buffer para logs en tiempo real (por defecto: 1).

Para el comando /last (MySQL):

- CLUSTER_DB_HOST: Host de MySQL (por defecto en codigo: dxspider-db).
- CLUSTER_DB_NAME: Nombre de la base de datos.
- CLUSTER_DB_USER: Usuario de la base de datos.
- CLUSTER_DB_PASS: Contrasena de la base de datos.

Variables de proxy opcionales:

- HTTP_PROXY
- HTTPS_PROXY
- http_proxy
- https_proxy
- NO_PROXY

## Configuracion y ejecucion local (sin Docker)

1. Instalar dependencias:

```bash
pip install -r requirements.txt
```

2. Exportar variables de entorno:

```bash
export BOT_TOKEN="tu_token_de_telegram"
export SPIDER_HOST="dxspider"
export SPIDER_PORT="23"
export MY_CALL="TU_INDICATIVO"

# Opcional, solo para /last
export CLUSTER_DB_HOST="spider_database"
export CLUSTER_DB_NAME="tu_db"
export CLUSTER_DB_USER="tu_usuario"
export CLUSTER_DB_PASS="tu_password"
```

3. Ejecutar el bot:

```bash
python main.py
```

## Configuracion y ejecucion con Docker Compose

Este es el modo de despliegue recomendado para este bot.

1. Crear archivo local de variables desde el ejemplo y poner ahi los secretos:

```bash
cp .env.example .env
```

2. Crear archivo compose desde el ejemplo:

```bash
cp docker-compose.yml.sample docker-compose.yml
```

3. Editar .env y ajustar al menos:

- BOT_TOKEN
- SPIDER_HOST
- SPIDER_PORT
- MY_CALL
- CLUSTER_DB_NAME
- CLUSTER_DB_USER
- CLUSTER_DB_PASS

4. Iniciar servicio:

```bash
docker compose up -d --build
```

5. Ver logs:

```bash
docker compose logs -f dx-telegram-bot
```

## Comandos del bot

### /setfilter - Crear o actualizar filtro

Sintaxis flexible para crear alertas:

- `/setfilter <CALL>` - Todas las bandas, todos los modos
- `/setfilter <CALL> <bandas>` - Bandas específicas, todos los modos
- `/setfilter <CALL> <modos>` - Todas las bandas, modos específicos
- `/setfilter <CALL> * <modos>` - Todas las bandas, modos específicos
- `/setfilter <CALL> <bandas> <modos>` - Bandas y modos específicos

**Bandas:** `160,80,60,40,30,20,17,15,12,10,6,4,2,UHF` (separadas por comas, o `ALL`/`*`)  
**Modos:** `SSB,CW,DIGI,FT8` (separados por comas, o `ALL`/`*`)

Ejemplos:
- `/setfilter EA1ABC` → alertas para EA1ABC en todas bandas/modos
- `/setfilter EA1ABC 40,20` → EA1ABC en 40m y 20m, todos los modos
- `/setfilter EA1ABC FT8,CW` → EA1ABC en todas las bandas, solo FT8 y CW
- `/setfilter EA1ABC * FT8` → EA1ABC en todas bandas, solo FT8
- `/setfilter EA1ABC ALL ALL` → lo mismo que `/setfilter EA1ABC`

### Otros comandos

- `/start` - Iniciar el bot y mostrar mensaje de bienvenida
- `/help` - Mostrar guía de comandos
- `/myfilters` - Ver filtros activos (pulsa botón para borrar)
- `/clearallfilters` - Borrar todos tus filtros (requiere confirmación en botones)
- `/last <CALL>` - Ver los últimos 10 spots de los últimos 30 minutos para un indicativo
- `/rbn on|off` - Activar o desactivar spots RBN (Skimmer) en tus alertas
- `/about` - Mostrar información del bot

## Persistencia de datos

- El archivo SQLite se guarda en /app/data dentro del contenedor.
- En el ejemplo de compose, ese directorio se monta desde ./bot_data en el host.

## Notas

- Si se pierde la conexion con DXSpider, el bot reintenta automaticamente.
- Los spots duplicados se filtran durante 10 minutos.
