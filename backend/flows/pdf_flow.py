from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.agents.pdf_agent import run_pdf_agent

PDF_CACHE_TTL_SECONDS = 60 * 60


def _pdf_cache_dir(user_id: str) -> Path:
    cache_dir = Path(tempfile.gettempdir()) / "n7chat-pdf-cache" / user_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cleanup_user_pdf_cache(user_id: str, ttl_seconds: int = PDF_CACHE_TTL_SECONDS) -> None:
    threshold = datetime.now(timezone.utc).timestamp() - ttl_seconds
    for path in _pdf_cache_dir(user_id).glob("*.pdf"):
        try:
            if path.stat().st_mtime < threshold:
                path.unlink()
        except OSError:
            continue


async def build_pdf_report_flow(
    *,
    message: str,
    user: dict[str, Any],
    history: list[dict[str, str]] | None = None,
    data_context: dict[str, Any] | None = None,
    ttl_seconds: int = PDF_CACHE_TTL_SECONDS,
) -> dict[str, Any]:
    """Build a PDF and keep it temporarily in a per-user server cache."""
    result = await run_pdf_agent(
        message=message,
        user=user,
        data_context=data_context or {},
    )
    artifact = result.get("artifact") if isinstance(result.get("artifact"), dict) else {}
    file_path = result.get("file_path") or artifact.get("file_path")
    if not file_path:
        return result

    local_path = Path(file_path)
    user_id = str(user["sub"])
    _cleanup_user_pdf_cache(user_id, ttl_seconds)

    cached_path = _pdf_cache_dir(user_id) / local_path.name
    if local_path.resolve() != cached_path.resolve():
        shutil.copy2(local_path, cached_path)

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    download_url = f"/chat/artifacts/pdf/{cached_path.name}"
    updated_artifact = {
        **artifact,
        "file_name": cached_path.name,
        "file_path": str(cached_path),
        "download_url": download_url,
        "mime_type": "application/pdf",
        "storage": "server_cache",
        "expires_at": expires_at.isoformat(),
    }
    return {
        **result,
        "answer": f"Le PDF {artifact.get('type', 'rapport')} est pret.",
        "artifact": updated_artifact,
        "file_path": str(cached_path),
        "file_url": download_url,
        "storage": "server_cache",
        "expires_at": expires_at.isoformat(),
    }
