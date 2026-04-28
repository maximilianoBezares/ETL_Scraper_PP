import asyncio as asyn
from .base_page import BasePage

class SodimacPage(BasePage):
    def __init__(self, page):
        super().__init__(page, "Sodimac")
        self.selector_boton_next = "button#testId-pagination-bottom-arrow-right"
        self.selector_material = "div[data-testid='ssr-pod']"
        self.selector_nombre = "b.pod-subTitle"
        self.selector_marca = "b.pod-title"
        self.selector_proveedor = "b.pod-sellerText"
        self.selector_precio = "li.prices-1 span"
        self.selector_link = "a"
        self.selector_imagen = "img"

    async def extraer_por_catalogo(self, url):
        self.logger.info("Navegando a Sodimac Catalogo: %s...", url)
        await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        materiales = []
        num_pagina = 1
        
        while True:
            self.logger.info("Procesando página %d...", num_pagina)
            boton_next = self.page.locator(self.selector_boton_next)
            for i in range(3): 
                await self.page.mouse.wheel(0, 800)
                await self.page.wait_for_timeout(600)
            try:
                await self.page.wait_for_selector(self.selector_material, timeout=15000)
                materiales_pagina = await self.page.locator(self.selector_material).all()
                for item in materiales_pagina:
                    try:
                        nombre_node    = item.locator(self.selector_nombre).first
                        marca_node     = item.locator(self.selector_marca).first
                        precio_node    = item.locator(self.selector_precio).first
                        proveedor_node = item.locator(self.selector_proveedor).first
                        link_node      = item.locator(self.selector_link).first
                        imagen_node    = item.locator(self.selector_imagen).first
                        
                        nombre    = await nombre_node.inner_text(timeout=2000)
                        marca     = await marca_node.inner_text(timeout=2000)
                        precio    = await precio_node.inner_text(timeout=2000)
                        proveedor = await proveedor_node.inner_text(timeout=2000)
                        link      = await link_node.get_attribute("href", timeout=2000) or ""
                        imagen    = await imagen_node.get_attribute("src", timeout=2000) or ""
                        
                        materiales.append({
                            "nombre":    nombre.strip(),
                            "marca":     marca.strip(),
                            "precio":    precio.strip(),
                            "proveedor": proveedor.strip(),
                            "link":      link,
                            "imagen":    imagen
                        })
                    except:
                        continue 
            except Exception as e:
                self.logger.error("Error al localizar productos en pág %d: %s", num_pagina, e)

            if await boton_next.is_visible():
                try:
                    nombre_ref = await self.page.locator(self.selector_nombre).first.inner_text(timeout=5000)
                except:
                    nombre_ref = ""
                self.logger.info("Nombre referencia antes de click: %s", nombre_ref.strip())
                await boton_next.scroll_into_view_if_needed()
                await boton_next.click(force=True)
                cambio_exitoso = False
                for intento in range(15):
                    await self.page.wait_for_timeout(1000)
                    try:
                        nombre_ahora_node = self.page.locator(self.selector_nombre).first
                        nombre_ahora = await nombre_ahora_node.inner_text(timeout=1000)
                        self.logger.info("Intento %d: Nombre ahora: %s", intento, nombre_ahora.strip())
                        if nombre_ahora.strip() != nombre_ref.strip():
                            cambio_exitoso = True
                            num_pagina += 1
                            self.logger.info("Cambio a página %d detectado.", num_pagina)
                            break
                    except:
                        await self.page.mouse.wheel(0, 300)
                        continue
                if not cambio_exitoso:
                    self.logger.warning("Timeout: El contenido no cambió en pág %d. Finalizando.", num_pagina)
                    break
            else:
                break
        return materiales