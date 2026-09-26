# Voice Task Organizer & Notion / Obsidian / Calendar Sync

Organizador visual de tareas por dictado de voz (100% Free Tier) que convierte notas habladas en tarjetas interactivas con listas de comprobación y las sincroniza automáticamente con **Notion**, **Obsidian** y **Google Calendar**.

## Características Principales

* 🎙️ **Dictado Continuo por Voz**: Transcripción en tiempo real en español utilizando la Web Speech API nativa (sin consumo de cuotas ni APIs de pago).
* 🧠 **Parser Inteligente de Lenguaje Natural**: Extrae automáticamente el título, categoría (`Trabajo`, `Personal`, `Ideas`, `Proyectos`), prioridad (`Alta`, `Media`, `Baja`), fecha/hora y pasos de comprobación.
* 📅 **Tablero Visual por Días**: Organización automática de tarjetas en columnas dinámicas (*Hoy*, *Mañana*, *Próximos Días*, *Sin Fecha / Backlog*).
* ✏️ **Tarjetas 100% Editables**: Modificación in-situ de títulos, categorías, prioridades, fechas y pasos de listas de chequeo.
* 📓 **Integración con Obsidian**: Exportación de notas en Markdown con metadatos YAML frontmatter a tu Vault local y carpetas personalizadas (`OBSIDIAN_FOLDER`).
* 📘 **Integración con Notion**: Creación automática de páginas con bloques to-do interactivos a través de la API oficial de Notion.
* 🗓️ **Google Calendar**: Generación instantánea de eventos agendados con checklist.

## Estructura del Proyecto

```
.
├── server.py              # Servidor backend FastAPI (endpoints API & servidor estático)
├── voice_parser.py        # Parser de lenguaje natural en español para transcripciones de voz
├── notion_client.py       # Cliente HTTP de Notion API para creación de páginas y bloques to-do
├── cli.py                 # Interfaz CLI para carga en lote desde archivos JSON
├── static/
│   └── index.html         # Dashboard web con interfaz visual, dictado y tablero Kanban
├── docs/
│   └── adr/               # Registro de Decisiones de Arquitectura (ADR)
├── CHANGELOG.md           # Historial de cambios
├── .env.example           # Plantilla de variables de entorno
└── requirements.txt       # Dependencias del proyecto
```

## Configuración

1. Clonar e instalar dependencias:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

2. Configurar `.env`:

```env
NOTION_TOKEN=secret_xxx
NOTION_DATA_SOURCE_ID=xxx

# Opcional: Ruta local y carpeta de tu Vault de Obsidian
OBSIDIAN_VAULT_PATH="/Users/tu_usuario/Obsidian/MiVault"
OBSIDIAN_VAULT_NAME="MiVault"
OBSIDIAN_FOLDER="Substack"
```

## Ejecución

Para iniciar la aplicación web:

```bash
python3 -m uvicorn server:app --reload --port 8085
```

Abrí tu navegador en `http://localhost:8085`.

## Licencia

MIT
