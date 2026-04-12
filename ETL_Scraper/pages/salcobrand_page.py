import asyncio
import random
from .base_page import BasePage

class SalcobrandPage(BasePage):
    def __init__(self, page):
        super().__init__(page, "Salcobrand")
        # Selectores actualizados según el HTML real del catálogo
        self.selector_producto = "li.ais-Hits-item" 
        self.selector_nombre = ".product-info.truncate"
        self.selector_precio = ".display-price-normal, .display-offer-price"

    async def extraer_por_catalogo(self,url):
        url_catalogo = url
        self.logger.info(f"Navegando a {url_catalogo}...")
        await self.page.goto(url_catalogo, wait_until="domcontentloaded", timeout=60000)
        
        products = []
        num_pagina = 1
        
        while True:
            self.logger.info(f"--- INICIO PROCESAMIENTO PÁGINA {num_pagina} ---")
            
            # A. SCROLL SUAVE PARA ACTIVAR ALGOLIA
            await self.page.mouse.wheel(0, 500)
            await self.page.wait_for_timeout(3000)

            # B. DETECTAR PRODUCTOS
            try:
                await self.page.wait_for_selector(self.selector_producto, state="attached", timeout=15000)
                productos_actuales = await self.page.locator(self.selector_producto).all()
                print(f"DEBUG: Detectados {len(productos_actuales)} productos en pág {num_pagina}")
                
                if len(productos_actuales) == 0:
                    break

                # C. EXTRACCIÓN
                for item in productos_actuales:
                    try:
                        nombre = await item.locator(self.selector_nombre).first.inner_text(timeout=2000)
                        precio = await item.locator(self.selector_precio).first.inner_text(timeout=2000)
                        products.append({
                            "nombre": nombre.strip(), 
                            "precio": precio.strip(),
                        })
                    except:
                        continue
            except Exception as e:
                print(f"DEBUG: Error buscando productos: {e}")
                break

            # D. PAGINACIÓN
            boton_next = self.page.get_by_role("link", name="»").last
            
            if await boton_next.is_visible():
                # Guardar referencia para confirmar cambio
                nombre_ref = await self.page.locator(self.selector_nombre).first.inner_text()
                
                await boton_next.scroll_into_view_if_needed()
                await boton_next.click(force=True)
                
                # E. ESPERA DEL CAMBIO (EL GUARDIÁN)
                cambio_exitoso = False
                for intento in range(15):
                    await self.page.wait_for_timeout(1000)
                    try:
                        nombre_ahora = await self.page.locator(self.selector_nombre).first.inner_text(timeout=1000)
                        if nombre_ahora.strip() != nombre_ref.strip():
                            print(f"DEBUG: ¡Página {num_pagina + 1} cargada con éxito!")
                            cambio_exitoso = True
                            num_pagina += 1
                            break
                    except:
                        pass
                    
                    if intento == 7: # Scroll de rescate si no cambia
                        await self.page.mouse.wheel(0, -300)
                        await self.page.mouse.wheel(0, 300)

                if not cambio_exitoso:
                    print(f"DEBUG: La página {num_pagina} no cambió. Terminando extracción.")
                    break
            else:
                print("DEBUG: Fin del catálogo alcanzado.")
                break

        # IMPORTANTE: return fuera del while
        return products