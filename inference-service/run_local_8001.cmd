@echo off
rem AI-07: runtime :8001 that cua lan Claude (checkpoint canonical, Milvus stack Codex). Log: D:\tmp\ai07_runtime\inference_8001.log
rem Chay doc lap: powershell Start-Process cmd.exe -ArgumentList '/c','E:\traning_ai\inference-service\run_local_8001.cmd' -WindowStyle Hidden
cd /d E:\traning_ai\inference-service
set PYTHONPATH=..\ai-core
echo START %DATE% %TIME% >> D:\tmp\ai07_runtime\inference_8001.log
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 >> D:\tmp\ai07_runtime\inference_8001.log 2>&1
echo EXIT %ERRORLEVEL% %DATE% %TIME% >> D:\tmp\ai07_runtime\inference_8001.log
