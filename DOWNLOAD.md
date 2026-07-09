# Download Persona

## Which zip should I get?

| Download | Size | Built-in offline AI | Notes |
|----------|------|---------------------|-------|
| **[Persona-Windows-portable.zip](https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-Windows-portable.zip)** | **~1.3 GB** | **Yes** | Recommended. llama.cpp + Fast + Balanced models included. |
| **[Persona-macOS-portable.zip](https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-macOS-portable.zip)** | **~85 KB** | **No** | Source + launcher only. Needs Python 3.11+, then Ollama, cloud API, or demo mode. |

If your download is only a few megabytes (or ~70–85 KB), you likely grabbed **macOS** or did not get the full **Windows** zip. The Windows build with bundled AI is **about 1.3 GB**.

All releases: https://github.com/ArmadilloArmada/personal-LLM/releases

---

## Windows (built-in offline AI)

Persona is a **standalone Windows desktop app**. No install wizard, no Python, no terminal.

**Download:** https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-Windows-portable.zip

### What's in the zip (~1.3 GB)

- `Persona.exe` and `_internal/` (PyInstaller app)
- `llama-server.exe` (llama.cpp)
- **Fast** model (~350 MB) — quick replies
- **Balanced** model (~700 MB) — default
- **Quality** model is **not** pre-bundled — download once from Settings (~2 GB, enables file & memory tools)

### How to run

1. **Unzip the entire zip file** — do not drag only `Persona.exe` out
2. Open the `Persona` folder
3. Double-click **`Persona.exe`**
4. The Persona window opens (or your browser at `http://127.0.0.1:8765`)

**Tip:** Run **`Create Desktop Shortcut.bat`** once to add Persona to your desktop.

The `_internal` folder must stay next to `Persona.exe`.

### If it won't open

1. Try **`Run Persona.bat`**
2. Check **`%USERPROFILE%\.persona\error.log`**
3. Right-click `Persona.exe` → **Run as administrator** (first launch only)
4. Allow through **Windows Defender** / antivirus
5. Confirm you unzipped **all** files from the zip (~1.3 GB total)

---

## macOS (no bundled LLM yet)

**Download:** https://github.com/ArmadilloArmada/personal-LLM/releases/latest/download/Persona-macOS-portable.zip

This zip is **small (~85 KB)** on purpose: it ships source code and a `Persona.command` launcher, **not** llama.cpp or GGUF models. Built-in offline AI is **Windows-only** today.

### How to run

1. Unzip anywhere
2. Double-click **`Persona.command`**
3. First launch creates `.venv` and installs Python deps (needs internet once)
4. In Settings, use **Demo**, **Ollama**, or a **cloud API key**

If macOS blocks the app: right-click → **Open** → **Open**.

Data is stored in `~/.persona/`.

### macOS + offline AI

Install [Ollama](https://ollama.com) and pull a model (e.g. `ollama pull llama3.2`), then select **Ollama** in Persona Settings.

Bundled offline AI for macOS is planned; track progress on GitHub Issues/PRs.
