# JIRO AI - Troubleshooting Guide

## Quick Diagnostics

**Always start here:**
```bash
python main.py --health
```
This runs a full check on: Python version, dependencies, API keys, audio, directories, plugins.

## Common Issues & Fixes

### 1. "No module named X"

**Cause**: Missing Python package.

```bash
# Fix: Install the missing package
pip install X

# Or reinstall everything:
pip install -r requirements.txt

# If pip fails, try:
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. "config.json not found"

**Cause**: Config file missing or corrupted.

```bash
# Fix: Run setup to create it
python main.py --setup

# Or manually create config.json - copy the template from the repo
```

### 3. API Keys Not Working

**Symptoms**: "No API keys configured" or empty responses.

```bash
# Check which keys are configured:
python main.py --health

# Re-enter keys:
python main.py --setup
```

**Where to get API keys (all free tiers available):**
- Groq: https://console.groq.com → Create API Key
- Gemini: https://aistudio.google.com → Get API Key
- NVIDIA: https://build.nvidia.com → sign up → get key
- HuggingFace: https://huggingface.co/settings/tokens
- OpenRouter: https://openrouter.ai/keys

### 4. Audio / Voice Not Working

**Symptoms**: "No microphone detected" or "PortAudio" errors.

```bash
# Check audio devices:
python -c "import sounddevice; print(sounddevice.query_devices())"

# If sounddevice fails:
pip install sounddevice

# On Linux, install PortAudio first:
sudo apt install portaudio19-dev
pip install sounddevice
```

**ffmpeg not found (TTS won't play audio):**
```bash
# Windows:
winget install ffmpeg
# Or download from https://ffmpeg.org/download.html

# Linux:
sudo apt install ffmpeg

# Mac:
brew install ffmpeg
```

### 5. GUI Not Starting

**Cause**: CustomTkinter or Tkinter not available.

```bash
# Fix 1: Install CustomTkinter
pip install customtkinter

# Fix 2: Use CLI mode instead
python main.py --cli

# Fix 3: On Linux, install Tkinter
sudo apt install python3-tk
```

### 6. "Permission denied" Errors

**Windows**: Run Command Prompt as Administrator.

**Linux/Mac**:
```bash
# Don't use sudo with pip! Instead:
pip install --user -r requirements.txt
```

### 7. Slow Performance on Low-End PCs

**Tips:**
1. Use `--cli` mode (no GUI overhead)
2. Disable monitoring in config.json: `"monitoring": {"enabled": false}`
3. Disable proactive mode: `"proactive": {"enabled": false}`
4. Use only Groq API (fastest provider)
5. Don't download offline models unless you have 8GB+ RAM

### 8. Plugin Errors

**Symptoms**: "Plugin X has errors" in health check.

```bash
# Check plugin syntax:
python -c "import plugins.your_plugin"

# If Jiro's self-fixer can fix it:
# It auto-detects and attempts fixes on startup.

# Manual fix: Check the plugin file for:
# - Missing imports
# - Syntax errors
# - Wrong class inheritance (must inherit PluginBase)
```

### 9. "Connection refused" / Network Errors

**Cause**: No internet or API endpoint down.

**Fixes:**
1. Check internet connection
2. Check if API provider is down (Groq status: https://status.groq.com)
3. Enable offline mode: set `"offline": {"enabled": true}` in config.json
4. Download offline model: `python main.py --setup` → select "Download offline model"

### 10. Offline Model Issues

```bash
# Check if model is downloaded:
python -c "from core.offline_model_manager import OfflineModelManager; m = OfflineModelManager({}); print(m.get_status())"

# Manually download during setup:
python main.py --setup

# If llama-cpp-python fails to install:
# Windows: You need Visual Studio Build Tools
# Install from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Then: pip install llama-cpp-python
```

## Debugging Steps

### Step 1: Check Logs
```bash
# View recent logs:
type data\logs\jiro.log         # Windows
cat data/logs/jiro.log           # Linux/Mac

# Logs show timestamped errors with component names
```

### Step 2: Health Check
```bash
python main.py --health
# Shows: system info, Python version, dependencies, API keys, audio, plugins
```

### Step 3: Test Individual Components
```python
# Test AI (run in Python):
import asyncio, json
config = json.load(open("config.json"))
from ai.brain import Brain
brain = Brain(config)
print(asyncio.run(brain.process("hello")))

# Test TTS:
from voice.tts import TextToSpeech
tts = TextToSpeech(config)
asyncio.run(tts.speak("Hello, I am Jiro"))

# Test plugins:
from plugins.plugin_loader import PluginLoader
loader = PluginLoader(config)
plugins = loader.load_all()
print([p.name for p in plugins.values()])
```

### Step 4: Self-Fixer
Jiro has a built-in self-fixer. When errors occur:
1. It identifies the error type
2. Tries built-in fixes (install packages, create directories, repair config)
3. If available, asks the AI for suggestions
4. Logs everything to `data/logs/jiro.log`

### Step 5: Fresh Start
```bash
# Reset everything (keeps your config):
rmdir /s /q data          # Windows
rm -rf data               # Linux/Mac

# Full reset:
rmdir /s /q venv data     # Windows
rm -rf venv data          # Linux/Mac

# Then re-setup:
setup.bat                  # Windows
# Or: pip install -r requirements.txt && python main.py --setup
```

## Self-Fix System

Jiro has automatic error diagnosis and repair:

| Error Type | Auto-Fix |
|-----------|----------|
| Missing package | `pip install` automatically |
| Missing config.json | Creates default config |
| Missing directories | Creates them |
| Broken plugin | Tries AI-powered code fix |
| JSON parse error | Repairs or recreates file |
| Network error | Suggests checking connection |

The self-fixer works with:
1. **Built-in strategies** for common issues
2. **Offline LLM** (if downloaded) for code fixes
3. **Online AI APIs** for complex debugging

All fixes are logged in `data/logs/jiro.log`.

## Getting Help

If nothing works:
1. Run `python main.py --health` and save the output
2. Check `data/logs/jiro.log` for detailed errors
3. Open an issue on GitHub with the health report and log excerpts
