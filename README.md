# JIRO AI - Your Personal AI Assistant

A JARVIS-like personal AI assistant that works on Windows (including low-end PCs). Voice control, multi-provider AI, activity monitoring, smart automation, and more.

## Quick Start

### Windows (Recommended)
```
1. Install Python 3.10+ from https://python.org (check "Add to PATH")
2. Download/clone this project
3. Double-click setup.bat
4. Done! Jiro auto-starts on boot.
```

### Manual Setup
```bash
git clone https://github.com/MubasshirBadhon/Jiro-AI.git
cd Jiro-AI
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
python main.py --setup
python main.py
```

## Features

### Voice
- **Wake Word**: Say "Hey Jiro" to activate
- **Speech-to-Text**: Groq Whisper API (fast, accurate)
- **Text-to-Speech**: Edge TTS, streams sentence-by-sentence (speaks while thinking)

### AI Brain (Multi-Provider)
```
User Prompt → NVIDIA (understand & route)
                ↓
    ┌──── Groq (fast) ──────┐
    │                         │ → Combiner → Response
    └──── Gemini (deep) ─────┘
              ↓
    HuggingFace (heavy tasks like image gen)
              ↓
    OpenRouter (fallback)
              ↓
    Offline LLM (no internet)
```

### Monitoring & Productivity
- Active window tracking with category detection
- Automatic distraction warnings ("Stop scrolling Facebook!")
- Auto-close distracting tabs (configurable)
- Study topic detection + auto-quizzing
- Activity stats dashboard

### Smart Automation
- **Bengali + English NLP**: "5 tay call dio" → alarm at 5 PM
- **Auto-reminder extraction**: Detects tasks in messages automatically
- **Schedule awareness**: Knows if you're free or busy
- **Tab control**: Can close distracting windows

### Plugin System
Drop any `*_plugin.py` file into `plugins/` — it auto-loads. No editing main.py.
- Built-in: alarm, schedule, PDF analyzer, productivity
- AI-generated: "generate plugin weather checker" → creates one automatically

### Memory
- **Short-term**: Current session context
- **Long-term**: SQLite database across sessions
- **Self-training**: Learns your patterns over time

### Security
- Passkey authentication
- File integrity checking (detects tampering)

### Offline Mode
Auto-detects your PC specs and downloads the right model:
| Your PC | Model | Size |
|---------|-------|------|
| 16GB+ RAM, 8GB+ VRAM | Mistral 7B | 4.4 GB |
| 8GB+ RAM, 4GB+ VRAM | Phi-3 Mini | 2.3 GB |
| Low-end / No GPU | TinyLlama | 0.7 GB |

## Usage Modes

```bash
python main.py              # Full GUI + voice + monitoring
python main.py --cli        # Text-only CLI mode
python main.py --health     # System health check
python main.py --setup      # Interactive first-time setup
python main.py --dashboard  # Activity stats
python main.py --set-passkey # Set/change passkey
```

## File Structure

```
JIRO/
├── main.py                     # Entry point & orchestrator
├── config.json                 # All settings + API keys
├── permissions.json            # User consent records
├── setup.bat                   # One-click Windows setup
├── requirements.txt            # Python dependencies
│
├── core/                       # Core system
│   ├── permission_manager.py   # First-time consent system
│   ├── api_key_manager.py      # API key management + Supabase
│   ├── health_checker.py       # System health monitoring
│   ├── offline_model_manager.py # Device detection + LLM download
│   └── self_fixer.py           # Auto-diagnose & fix errors
│
├── voice/                      # Voice I/O
│   ├── stt.py                  # Speech-to-Text (Groq Whisper)
│   └── tts.py                  # Text-to-Speech (Edge TTS, streaming)
│
├── ai/                         # AI providers
│   ├── brain.py                # NVIDIA task router + orchestrator
│   ├── groq_handler.py         # Groq API (fast generation)
│   ├── gemini_handler.py       # Google Gemini API (deep)
│   ├── huggingface_handler.py  # HuggingFace API (heavy tasks)
│   ├── combiner.py             # Merges Groq + Gemini responses
│   └── offline_handler.py      # Local GGUF model inference
│
├── monitoring/                 # Activity tracking
│   ├── screen_monitor.py       # Active window tracking
│   ├── activity_recorder.py    # Full activity logger
│   └── message_reader.py       # Message analysis + task extraction
│
├── automation/                 # Smart automation
│   ├── alarm_manager.py        # Bengali + English NLP alarms
│   ├── schedule_manager.py     # Calendar + availability
│   ├── tab_controller.py       # Auto-close distracting tabs
│   └── reminder_extractor.py   # Auto-extract reminders from text
│
├── plugins/                    # Plugin system
│   ├── plugin_loader.py        # Auto-discovery + PluginBase class
│   ├── plugin_generator.py     # AI generates new plugins
│   ├── api_key_prompter.py     # Popup for missing API keys
│   ├── alarm_plugin.py         # Built-in alarm plugin
│   ├── schedule_plugin.py      # Built-in schedule plugin
│   ├── pdf_analyzer_plugin.py  # Built-in PDF plugin
│   └── productivity_plugin.py  # Built-in productivity plugin
│
├── memory/                     # Memory system
│   ├── short_term.py           # Session memory (in-memory)
│   ├── long_term.py            # Persistent memory (SQLite)
│   └── self_trainer.py         # Pattern learning + insights
│
├── ui/                         # User interface
│   ├── overlay.py              # Always-on-top dark GUI
│   ├── pdf_analyzer.py         # PDF text + image extraction
│   └── dashboard.py            # Monitoring transparency view
│
├── security/                   # Security
│   ├── passkey.py              # Authentication system
│   └── integrity_checker.py    # File tampering detection
│
└── data/                       # Runtime data (gitignored)
    ├── memory/                 # SQLite DB + activity logs
    ├── recordings/screenshots/ # Screen captures
    ├── models/                 # Offline LLM models
    └── logs/                   # Application logs
```

## API Keys

Add your keys to `config.json` or run `python main.py --setup`:

| Provider | Get Key | Used For |
|----------|---------|----------|
| **Groq** (recommended) | [console.groq.com](https://console.groq.com) | STT + fast AI |
| **Gemini** | [aistudio.google.com](https://aistudio.google.com) | Deep AI responses |
| **NVIDIA** | [build.nvidia.com](https://build.nvidia.com) | Task understanding |
| **HuggingFace** | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | Heavy compute |
| **OpenRouter** | [openrouter.ai](https://openrouter.ai) | Fallback |

**Minimum**: You need at least **one** API key (Groq recommended — it's free).

## Creating Plugins

1. Create `plugins/my_thing_plugin.py`
2. Inherit from `PluginBase`
3. Done — it auto-loads!

```python
from plugins.plugin_loader import PluginBase

class WeatherPlugin(PluginBase):
    name = "weather"
    description = "Check the weather"
    triggers = ["weather", "temperature", "forecast"]

    async def execute(self, command, context=None):
        return "It's sunny and 25°C today!"
```

Or let Jiro create one: `"generate plugin that checks weather"`

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed debugging guide.

**Quick fixes:**
- `No module named X` → `pip install X`
- `No API keys` → Edit `config.json` or run `--setup`
- `Audio not working` → Install ffmpeg: `winget install ffmpeg`
- `GUI not starting` → Run `python main.py --cli` for text mode
- Any error → Run `python main.py --health` for diagnostics

## License

MIT License - use freely, modify as you wish.
