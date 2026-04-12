import asyncio
import random
from .base_page import BasePage

class KnopPage(BasePage):
    def __init__(self, page):
        super().__init__(page, "Knop")
        # Selector corregido con puntos para clases múltiples
        self.selector_producto = ".product-item" # Más simple y robusto
        self.selector_nombre = ".product-model"
        self.selector_precio = ".bootic-price"
        # Selector específico para el enlace que pusiste
        self.selector_next = "a.next_page" 

    async def extraer_por_catalogo(self, url):

        self.logger.info(f"Navegando a Knop: {url}...")
        await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        products = []
        num_pagina = 1
        
        while True:
            self.logger.info(f"--- PROCESANDO PÁGINA {num_pagina} ---")
            
            # A. SCROLL PARA CARGA DINÁMICA
            await self.page.mouse.wheel(0, 1000)
            await self.page.wait_for_timeout(2000)

            # B. DETECTAR PRODUCTOS
            try:
                # Esperamos a que aparezca al menos uno
                await self.page.wait_for_selector(self.selector_producto, timeout=15000)
                
                # C. EXTRACCIÓN RÁPIDA (Vía JavaScript para evitar Timeouts)
                productos_data = await self.page.evaluate(f"""() => {{
                    const items = document.querySelectorAll('{self.selector_producto}');
                    return Array.from(items).map(item => ({{
                        nombre: item.querySelector('{self.selector_nombre}')?.innerText.trim() || '',
                        precio: item.querySelector('{self.selector_precio}')?.innerText.trim() || '0'
                    }}));
                }}""")

                print(f"DEBUG: Extraídos {len(productos_data)} productos de la página {num_pagina}")
                
                for p in productos_data:
                    if p['nombre']:
                        p['pharmacy'] = 'knop'
                        products.append(p)

            except Exception as e:
                print(f"DEBUG: No se detectaron productos: {e}")
                break

            # D. PAGINACIÓN (Basado en tu <a> tag)
            # Usamos el selector CSS exacto del rel='next'
            boton_next = self.page.locator(self.selector_next).first
            
            if await boton_next.is_visible():
                # Guardamos el primer nombre para el Guardián
                nombre_ref = products[-1]['nombre'] if products else ""
                
                print("Click en Siguiente »")
                await boton_next.scroll_into_view_if_needed()
                await boton_next.click(force=True)
                
                # E. EL GUARDIÁN DEL CAMBIO
                cambio_exitoso = False
                for intento in range(12):
                    await self.page.wait_for_timeout(1000)
                    # Verificamos si el primer producto de la nueva página es distinto
                    try:
                        nombre_ahora = await self.page.locator(self.selector_nombre).first.inner_text(timeout=1000)
                        if nombre_ahora.strip() != nombre_ref:
                            num_pagina += 1
                            print(f"✅ ¡Página {num_pagina} detectada!")
                            cambio_exitoso = True
                            break
                    except:
                        pass
                
                if not cambio_exitoso:
                    print(f"⚠️ La página {num_pagina} se quedó pegada. Terminando.")
                    break
            else:
                print("🏁 Fin del catálogo alcanzado.")
                break

        return products