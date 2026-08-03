import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.ai.factory import create_ai_provider  # noqa: E402
from app.core.config import get_settings  # noqa: E402


async def check() -> int:
    settings = get_settings()
    provider = create_ai_provider(settings)
    try:
        status = await provider.status(force_refresh=True)
        print(f"Provider: {status.provider}")
        print(f"Base URL: {status.base_url}")
        print(f"Available: {status.available}")
        print(f"Version: {status.version or 'unknown'}")
        print(f"Configured model: {status.configured_model or 'not configured'}")
        print("Installed models:")
        if status.available:
            for model in await provider.list_models(force_refresh=True):
                size_gib = model.size / (1024**3)
                marker = " (configured)" if model.is_configured else ""
                details = model.details
                print(
                    f"  - {model.name}: {size_gib:.2f} GiB, "
                    f"{details.parameter_size or 'unknown parameters'}, "
                    f"{details.quantization_level or 'unknown quantization'}{marker}"
                )
        print(f"Ready: {status.model_ready}")
        print(status.message)
        if not status.model_ready:
            print("Next step: start Ollama or configure an exact installed model name.")
            return 1
        return 0
    finally:
        await provider.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check()))
