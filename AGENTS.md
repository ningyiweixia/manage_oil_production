# Agent Notes

## Local startup priority

When asked to start this project locally on Windows, prefer the verified startup method documented in `STARTUP_LOG.md`.

Use the `.local/start-backend.ps1` and `.local/start-frontend.ps1` helpers when present. If minimized background processes are requested, use the documented `cmd.exe /c start ... /min ...` commands instead of PowerShell `Start-Process`, because `Start-Process` previously failed in this environment with a duplicated `Path`/`PATH` environment-key conflict.
