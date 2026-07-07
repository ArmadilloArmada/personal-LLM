# WebView2 / pywebview spike notes

## Problem

Frozen `Persona.exe` fails to load pywebview because `pythonnet` cannot resolve `Python.Runtime.Loader.Initialize` from the bundled `Python.Runtime.dll` in `_internal/pythonnet/runtime/`.

## Current workaround (v1.0.3+)

Portable builds skip pywebview and open Edge/Chrome in `--app` mode with a system tray icon.

## Spike options

| Option | Effort | Notes |
|--------|--------|-------|
| Bundle pythonnet + clr_loader binaries in `persona.spec` | Medium | Added `pythonnet` and `clr_loader` to hiddenimports; may need explicit `collect_all('pythonnet')` in spec |
| Use WebView2 fixed runtime | Medium | Ship `Microsoft.WebView2.FixedVersionRuntime` beside exe |
| Tiny C# WebView2 host | Medium | `PersonaShell.exe` loads URL; Python exe stays backend-only |
| Keep Edge app mode | Low | Current production path |

## Recommendation

Ship Edge app mode + tray for v1.1. Revisit native WebView2 only if users reject browser shell or we add code signing for a dedicated host.

## Test locally

```powershell
pip install -e "./persona-app[desktop]"
pyinstaller persona-app/persona.spec --noconfirm
# Check startup.log for pywebview vs Edge fallback
```
