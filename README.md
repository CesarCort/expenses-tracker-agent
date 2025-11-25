# Spending Tracker Bot

Este es un agente LLM Based diseñado para rastrear y gestionar gastos personales a través de Telegram. Utiliza Google Gemini para interpretar mensajes (texto e imágenes) y registra la información en Google Sheets.

## Características

- 🗣️ **Lenguaje Natural:** Registra gastos escribiendo simplemente "Gaste 20 soles en comida".
- 📸 **Soporte de Imágenes:** Envía fotos de recibos o comprobantes para extracción automática de datos.
- 📊 **Resúmenes:** Consulta reportes de gastos entre fechas específicas.
- ☁️ **Google Sheets:** Todos los datos se sincronizan automáticamente con tu hoja de cálculo.

## Requisitos Previos

- Python 3.10 o superior.
- Una cuenta de Google Service Account con acceso a la API de Google Sheets y Drive.
- Un bot de Telegram (creado con @BotFather).

## Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/CesarCort/expenses-tracker-agent.git
   cd spending-tracker
   ```

2. **Crear un entorno virtual (recomendado):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuración

### 1. Credenciales de Google
Coloca tu archivo de credenciales de servicio (Service Account) en la siguiente ruta:
`secrets/creds.json` o cargalo directamente en tu environmente en la variables GOOGLE_CREDENTIALS_JSON.

Asegúrate de compartir tu Google Sheet (`home_expenses`) con el email de la cuenta de servicio. Si tu GoogleSheet file tiene diferente nombre, actualizalo.

### 2. Variables de Entorno
Crea un archivo `.env` en la carpeta `spending_tracker/` (ej. `spending_tracker/.env`) con el siguiente contenido:

```env
TELEGRAM_BOT_TOKEN=tu_token_del_bot_aqui
# Opcional si no usas archivo creds.json:
# GOOGLE_CREDENTIALS_JSON=contenido_json_minificado
```

## Ejecución

Para iniciar el bot, ejecuta el siguiente comando desde la raíz del proyecto:

```bash
python run_bot.py
```

El bot iniciará y podrás interactuar con él en Telegram.

