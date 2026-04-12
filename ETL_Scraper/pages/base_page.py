import logging as log
from datetime import datetime

log.basicConfig(
    level=log.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
    )

class BasePage:
    def __init__(self, page, name):
        self.page = page
        self.name = name
        self.logger = log.getLogger(name)

    async def navigate(self, url: str):
        self.logger.info(f"Navegando a: {url}...")
        try:
            await self.page.goto(url,wait_until="domcontentloaded", timeout =60000)
        except Exception as e:
            self.logger.error(f"Error al navegar a {url}: {e}")
            await self.page.screenshot(path=f"{self.name}_navigation_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            raise