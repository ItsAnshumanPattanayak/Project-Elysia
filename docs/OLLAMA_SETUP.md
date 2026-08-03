# Local Ollama Setup

Project Elysia Batch 2 communicates only with an explicitly configured Ollama service. The default URL is `http://127.0.0.1:11434`; there is no cloud fallback and the application never pulls a model automatically.

## Inspect and configure

```powershell
ollama --version
ollama list
cd E:\Project-Elysia\backend
& .\.venv\Scripts\python.exe scripts\check_ollama.py
```

Set `OLLAMA_MODEL` in the ignored `backend/.env` to an exact name returned by `ollama list`. To switch models, stop active generation, edit only that value, restart the backend, and run the check script again. `/api/ai/status?refresh=true` can force a harmless readiness refresh.

The inspected machine had one installed conversational model: `llama3.1:latest`, an 8B Llama-family GGUF using Q4_K_M quantization, approximately 4.9 GB, with completion/tool capabilities. It was selected because it is the only installed conversational/instruct model and is appropriate for general dialogue. It is not claimed to be universally best. With roughly 7.68 GiB system RAM and integrated graphics, loading or generation may be slow or may fail under memory pressure; close memory-heavy applications, lower `OLLAMA_CONTEXT_SIZE`, or select a smaller model that the user has installed manually.

If no suitable model exists, choose and manually run an appropriate `ollama pull <model>` command. Project Elysia will not run that command for you. Disk capacity should be checked first.

## Configuration

- `OLLAMA_BASE_URL`: trusted provider URL; loopback by default.
- `OLLAMA_MODEL`: exact locally installed model identifier.
- `OLLAMA_CONNECT_TIMEOUT_SECONDS`, `OLLAMA_READ_TIMEOUT_SECONDS`: bounded transport timeouts.
- `OLLAMA_KEEP_ALIVE`: Ollama model retention duration.
- `OLLAMA_TEMPERATURE`, `OLLAMA_TOP_P`, `OLLAMA_TOP_K`, `OLLAMA_REPEAT_PENALTY`: bounded defaults.
- `OLLAMA_CONTEXT_SIZE`, `OLLAMA_MAX_OUTPUT_TOKENS`: resource/output safeguards.
- `OLLAMA_STATUS_CACHE_TTL_SECONDS`: short-lived status/model cache only; generations are never cached.

## Troubleshooting

- **Unavailable:** start the installed Ollama application or `ollama serve`, then check `/api/version`.
- **Model not configured:** set an exact `OLLAMA_MODEL` value and restart.
- **Model not installed:** compare the configured value with `ollama list`; no automatic download occurs.
- **Timeout/model load failure:** check RAM and disk, reduce context/output limits, and inspect Ollama logs without sharing private prompts.
- **Plain-text fallback:** some models may ignore the JSON contract. The backend returns a safe parsed fallback and marks `parse_status` accordingly.

