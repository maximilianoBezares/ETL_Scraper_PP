import asyncio as asyn
from .base_page import BasePage

class CruzVerdePage(BasePage):
    def __init__(self, page):
        super().__init__(page, "CruzVerde")
        self.selector_boton = "ml-pagination div.bg-quaternary"
        self.selector_producto = "ml-new-card-product"
        self.selector_nombre = "h2 span"
        self.selector_precio = "p.text-green-turquoise"
        self.selector_boton_popup = "button#onesignal-slidedown-cancel-button"    

    async def extraer_por_catalogo(self, url):
        print(f"Navegando a {url}...")
        await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await self.cerrar_modal_inicial()
        
        products = []
        num_pagina = 1
        
        while True:
            botones = self.page.locator(self.selector_boton)
            cantidad = await botones.count()

            if num_pagina == 1:
                boton_next = botones.nth(0)
            elif cantidad == 4:
                boton_next = botones.nth(2)
            else:
                break 

            self.logger.info(f"Procesando página {num_pagina}...")
            
            # A. SCROLL REFORZADO
            for i in range(3): 
                await self.page.mouse.wheel(0, 800)
                await self.page.wait_for_timeout(600)

            # B. ESPERAR PRODUCTOS Y EXTRAER CON SEGURIDAD
            try:
                await self.page.wait_for_selector(self.selector_producto, timeout=15000)
                productos_pagina = await self.page.locator(self.selector_producto).all()
            
                for item in productos_pagina:
                    try:
                        # Usamos wait_for en lugar de ir directo al texto para evitar el timeout
                        nombre_node = item.locator(self.selector_nombre).first
                        precio_node = item.locator(self.selector_precio).first
                        
                        nombre = await nombre_node.inner_text(timeout=2000)
                        precio = await precio_node.inner_text(timeout=2000)
                        
                        products.append({
                            "nombre": nombre.strip(),
                            "precio": precio.strip(),
                        })
                    except:
                        continue 
            except Exception as e:
                self.logger.error(f"Error al localizar productos en pág {num_pagina}: {e}")

            # C. PAGINACIÓN
            if await boton_next.is_visible():
                try:
                    nombre_ref = await self.page.locator(self.selector_nombre).first.inner_text(timeout=5000)
                except:
                    nombre_ref = "" # Si falla, usamos vacío para forzar el cambio
                
                print(f"Nombre referencia antes de click: {nombre_ref.strip()}")
                await boton_next.scroll_into_view_if_needed()
                await boton_next.click(force=True)
            
                # D. GUARDIÁN ANTIFALLOS (Evita el error de la pág 150)
                cambio_exitoso = False
                for intento in range(15): # Aumentamos a 15 segundos para páginas lentas
                    await self.page.wait_for_timeout(1000)
                    try:
                        # El try previene el crash si el h2 span no aparece de inmediato
                        nombre_ahora_node = self.page.locator(self.selector_nombre).first
                        nombre_ahora = await nombre_ahora_node.inner_text(timeout=1000)
                        print(f"Intento {intento}: Nombre ahora: {nombre_ahora.strip()}")
                    
                        if nombre_ahora.strip() != nombre_ref.strip():
                            cambio_exitoso = True
                            num_pagina += 1
                            print(f"✅ ¡Cambio a página {num_pagina} detectado!")
                            break
                    except:
                        # Si no encuentra el nombre todavía, hace scroll para forzar carga
                        await self.page.mouse.wheel(0, 300)
                        continue

                if not cambio_exitoso:
                    self.logger.warning(f"Timeout: El contenido no cambió en pág {num_pagina}. Reintentando última acción.")
                    # Si no cambió, intentamos un refresh suave o salimos para no quedar en bucle
                    break
            else:
                break
        return products

    async def cerrar_modal_inicial(self):
        selector_btn = "button.bg-prices"
        try:
            await self.page.wait_for_selector(selector_btn, state="visible", timeout=8000)
            await self.page.click(selector_btn)
        except Exception:
            try:
                await self.page.evaluate(f"document.querySelector('{selector_btn}')?.click()")
            except:
                pass
        await self.page.wait_for_timeout(2000)