# Voice Task Organizer & Notion / Obsidian / Calendar Sync

Organizador visual de tareas por dictado de voz (100% Free Tier) que convierte notas habladas en tarjetas interactivas con listas de comprobación y las sincroniza automáticamente con **Notion**, **Obsidian** y **Google Calendar**.

> **"Soy Creadora. Tecnología para un fin"**  
> *Dictá tu nota ➔ Visualizá la tarjeta ➔ Sincronizá con Notion, Obsidian y Calendario*

---

## Características Principales

* 🎙️ **Dictado Continuo por Voz & Anglicismos**: Transcripción en tiempo real en español reconociendo términos técnicos y anglicismos (`deploy`, `meeting`, `PR`, `commit`, `merge`, `push`, `test`, `review`, `feedback`, `backup`, `issue`, `bug`, `feature`). Compatible con la Web Speech API nativa del navegador y con aplicaciones de dictado local avanzado como **Whisper Flow** para captura continua de alta precisión.
* 🔊 **Amazon Polly Neural Text-to-Speech**: Síntesis de voz en alta definición utilizando el motor **Neural** de Amazon Polly (`Lupe`, `Mia`, `Lucia`) a través del endpoint `/api/polly/stream`.
* ☁️ **Persistencia en la Nube con Firebase (Free Tier)**: Almacenamiento NoSQL de notas en **Cloud Firestore** y archivos de audio en **Cloud Storage** con la librería `firebase_client.py`.
* 🧠 **Parser Inteligente de Lenguaje Natural**: Desglose automático de dictados corridos en listas estructuradas con saltos de línea y viñetas (`•`).
* 📅 **Tablero Visual por Días**: Organización automática de tarjetas en columnas dinámicas (*Hoy*, *Mañana*, *Próximos Días*, *Sin Fecha / Backlog*).
* ✏️ **Tarjetas 100% Editables**: Modificación in-situ de títulos, categorías, prioridades, fechas y listas de chequeo con foco automático al agregar pasos.
* 📑 **Estado de Completado & Filtro**: Marcado de tarjetas completadas que permanecen activas hasta su resolución y se archivan limpiamente del tablero.
* 📓 **Guardado Silencioso en Obsidian**: Exportación de notas en Markdown con metadatos YAML frontmatter a tu carpeta local de Obsidian (`obsidian_vault/Substack`) en segundo plano sin desplegar la app de Obsidian.
* ⚡ **Sincronización Manos Libres por Voz**: Detección inteligente de comandos como `añadir a Notion`, `add to Obsidian`, `enviar a Notion` o `exportar a Obsidian` en la frase dictada para sincronizar directamente sin hacer clic.
* 💾 **Persistencia de Tablero Local (`localStorage`)**: Las tarjetas y listas editadas se conservan automáticamente entre sesiones y reinicios del navegador.

---

## Estructura del Proyecto

```
.
├── server.py              # Servidor backend FastAPI (endpoints API & servidor estático)
├── voice_parser.py        # Parser de lenguaje natural en español para transcripciones de voz
├── notion_client.py       # Cliente HTTP de Notion API para creación de páginas y bloques to-do
├── cli.py                 # Interfaz CLI para carga en lote desde archivos JSON
├── static/
│   └── index.html         # Dashboard web con interfaz visual, dictado y tablero Kanban
├── obsidian_vault/        # Carpetas locales de notas Markdown para Obsidian (Substack/)
├── docs/
│   └── adr/               # Registro de Decisiones de Arquitectura (ADR)
├── CHANGELOG.md           # Historial de cambios
├── .env.example           # Plantilla de variables de entorno
└── requirements.txt       # Dependencias del proyecto
```

---

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

# Ruta local del Vault de Obsidian del proyecto para guardado silencioso en segundo plano
OBSIDIAN_VAULT_PATH="/Users/elena/Developer/Personal Assistent/obsidian_vault"
OBSIDIAN_VAULT_NAME="obsidian_vault"
OBSIDIAN_FOLDER="Substack"
```

---

## Ejecución

Para iniciar la aplicación web:

```bash
python3 -m uvicorn server:app --reload --port 8085
```

Navegá en tu explorador a `http://localhost:8085`.

---

## Opciones de Dictado por Voz

La aplicación soporta dos modalidades de captura por voz:
1. **Web Speech API Nativa**: Incorporada en la aplicación web, funciona directo en el navegador haciendo clic en el icono del micrófono.
2. **Whisper Flow**: Integración perfecta con herramientas de dictado basadas en OpenAI Whisper local/cloud como **Whisper Flow**, permitiendo dictar directamente en el área de texto de cualquier tarjeta con puntuación automática y máxima precisión.

---

## Licencia

MIT
