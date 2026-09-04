from __future__ import annotations

from typing import Dict, Optional

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright


class BrowserManager:
    """Owns the Playwright driver + a single Chromium instance for one run."""

    def __init__(self) -> None:
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def start(self, headless: bool = True) -> None:
        self._pw = await async_playwright().start()
        try:
            self._browser = await self._pw.chromium.launch(headless=headless)
        except Exception as exc:  # pragma: no cover - environment specific
            raise RuntimeError(
                "Failed to launch Chromium. Make sure browsers are installed: "
                "`python -m playwright install chromium`. Original error: "
                f"{exc}"
            ) from exc

    async def new_context(
        self,
        viewport: Dict[str, int],
        timeout_ms: int,
        user_agent: Optional[str] = None,
        init_script: Optional[str] = None,
    ) -> BrowserContext:
        assert self._browser is not None, "BrowserManager.start() not called"
        context = await self._browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale="en-US",
            # scan without restrictions: tolerate sloppy/self-signed TLS
            ignore_https_errors=True,
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        context.set_default_timeout(timeout_ms)
        context.set_default_navigation_timeout(timeout_ms)
        if init_script:
            await context.add_init_script(init_script)
        return context

    async def stop(self) -> None:
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._pw is not None:
            try:
                await self._pw.stop()
            except Exception:
                pass
            self._pw = None
