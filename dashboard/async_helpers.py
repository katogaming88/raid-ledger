"""Async helpers for running coroutines from Streamlit's sync context."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any


def run_async(coro: Any) -> Any:
    """Run an async coroutine from synchronous Streamlit code.

    Handles the case where an event loop is already running
    (common in some Streamlit versions) by delegating to a thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop running — safe to use asyncio.run directly
        return asyncio.run(coro)

    # Loop already running — run in a separate thread
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
