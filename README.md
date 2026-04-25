# Jiro AI - Your Personal AI Assistant

Jiro AI is an intelligent, always-on personal assistant that lives on your desktop. It combines multiple AI providers for smart, context-aware responses, monitors your productivity, helps you study, manages your schedule, and acts as your day-to-day digital partner.

## Features

### Core
- **Voice Input/Output**: Speech-to-Text via Groq Whisper, streaming Text-to-Speech via Edge TTS (speaks sentence-by-sentence while generating)
- **Multi-Provider AI**: Smart routing across NVIDIA, Groq, Gemini, HuggingFace, and OpenRouter
- **Always-On-Top GUI**: Compact overlay with text and voice input, minimizable to a floating bubble
- **Wake Word Detection**: Say "Jiro" to activate voice mode
- **Bilingual**: Understands both English and Bengali (Bangla)

### Intelligence
- **Smart API Routing**: Uses NVIDIA for understanding prompts, Groq+Gemini combined for quality responses, HuggingFace for heavy compute tasks
- **Persistent Memory**: Remembers conversations, preferences, and patterns across sessions
- **Context Awareness**: Monitors active windows to understand what you're doing

### Plugins (Auto-loaded)
- **Alarm/Reminder**: Natural language alarm setting ("set alarm for 5 PM", "5 tay call dio")
- **Schedule Manager**: Track events, check availability, get smart reply suggestions
- **PDF Analyzer**: Extract text and images from PDFs, analyze content via AI
- **Productivity Tracker**: Monitor app usage, distraction warnings, screen time reports

### Proactive Assistant
- Warns about excessive time on distracting apps
- Quizzes you on recently studied topics
- Suggests productivity improvements
- Schedule reminders

### Monitoring
- Active window tracking for productivity insights
- Screen capture for context awareness
- Application usage statistics

## Quick Start

### Windows (Recommended)
```batch
:: Double-click setup.bat or run:
setup.bat
```
This will:
1. Create a Python virtual environment
2. Install all dependencies
3. Set up auto-start on Windows login
4. Launch Jiro AI

### Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

### Run Modes
```bash
python main.py              # Full mode with GUI
python main.py --cli        # CLI mode (text only, no GUI)
python main.py --no-gui     # Voice mode without GUI
python main.py --health     # Run health check
```

## Configuration

Edit `config.json` to set your API keys and preferences:

```json
{
    "api_keys": {
        "nvidia": "your-nvidia-api-key",
        "huggingface": "your-hf-token",
        "groq": "your-groq-api-key",
        "gemini": "your-gemini-api-key",
        "openrouter": "your-openrouter-key"
    },
    "supabase": {
        "backend_url": "your-supabase-url",
        "anon_key": "your-supabase-anon-key"
    }
}
```

API keys can also be stored in Supabase for secure remote access.

### Get API Keys
- **NVIDIA**: [build.nvidia.com](https://build.nvidia.com)
- **Groq**: [console.groq.com](https://console.groq.com)
- **Gemini**: [aistudio.google.com](https://aistudio.google.com)
- **HuggingFace**: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
- **OpenRouter**: [openrouter.ai/keys](https://openrouter.ai/keys)

## Creating Plugins

Drop a new `*_plugin.py` file in the `plugins/` folder - it will be auto-loaded!

```python
from core.plugin_loader import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"
    description = "What my plugin does"
    triggers = ["keyword1", "keyword2"]

    async def execute(self, command, context=None):
        # Your plugin logic here
        return "Plugin response"
```

No need to modify `main.py` - the plugin loader discovers and loads all `*_plugin.py` files automatically.

## Architecture

```
jiro-ai/
├── main.py                     # Main orchestrator
├── config.json                 # Configuration
├── setup.bat                   # Windows auto-setup
├── requirements.txt            # Dependencies
├── core/
│   ├── config_manager.py       # Configuration management
│   ├── stt.py                  # Speech-to-Text (Groq Whisper)
│   ├── tts.py                  # Text-to-Speech (Edge TTS, streaming)
│   ├── ai_engine.py            # Multi-provider AI routing
│   ├── plugin_loader.py        # Dynamic plugin system
│   └── wake_word.py            # Wake word detection
├── gui/
│   └── overlay.py              # Always-on-top GUI
├── plugins/
│   ├── alarm_plugin.py         # Alarms & reminders
│   ├── schedule_plugin.py      # Schedule management
│   ├── pdf_analyzer_plugin.py  # PDF analysis
│   └── productivity_plugin.py  # Productivity tracking
├── monitoring/
│   ├── screen_monitor.py       # Screen & window tracking
│   ├── activity_tracker.py     # Activity pattern analysis
│   └── proactive_assistant.py  # Proactive suggestions
├── utils/
│   ├── health_checker.py       # System health checks
│   └── memory.py               # Persistent memory
└── data/
    ├── memory/                 # Stored memories & schedules
    └── recordings/             # Screenshots & activity logs
```

## How It Works

1. **Input**: User speaks (wake word → STT) or types in the GUI
2. **Routing**: Input is checked against plugin triggers first, then sent to AI
3. **AI Pipeline**: NVIDIA analyzes the prompt → Groq + Gemini generate in parallel → responses are combined
4. **Output**: TTS speaks the response sentence-by-sentence while still generating; GUI shows the text
5. **Background**: Screen monitor tracks activity, proactive assistant watches for opportunities to help

## Requirements
- Python 3.10+
- Windows 10/11 (primary), Linux/Mac (partial support)
- Microphone (for voice input)
- Internet connection (for AI APIs)
- ffmpeg (for audio playback)
