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

    async def manejar_popups_emergentes(self):
        # Validacion de Cookies
        try:
            boton_cookies = self.page.get_by_role("button", name="Aceptar")
            if await boton_cookies.is_visible(timeout=500):
                await boton_cookies.click()
        except Exception:
            pass
        # clic al aire (Para cerrar modales haciendo clic en el fondo oscurecido)
        try:
            await self.page.mouse.click(5, 200)
        except Exception:
            pass
        # La tecla Escape (Estándar de accesibilidad web para modales)
        try:
            await self.page.keyboard.press("Escape")
        except Exception:
            pass
        # Cazar botones de cierre (X) genéricos
        try:
            # Busca cualquier botón que tenga "close" o "cerrar" en sus clases o atributos
            btn_cerrar = self.page.locator('button[class*="close"], button[aria-label*="errar"], i[class*="close"]').first
            if await btn_cerrar.is_visible(timeout=500):
                await btn_cerrar.click(force=True)
        except Exception:
            pass  
        await self.page.wait_for_timeout(500)