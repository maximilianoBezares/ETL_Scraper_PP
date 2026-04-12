import asyncio
import random
from .base_page import BasePage

class DrsimiPage(BasePage):
    def __init__(self, page):
        super().__init__(page, "DrSimi")
        # Selectores (Vamos a verificar estos con el debugger)
        self.selector_producto = "section.vtex-product-summary-2-x-container"
        self.selector_nombre = ".vtex-product-summary-2-x-brandName"
        self.selector_precio = ".vtex-product-price-1-x-sellingPriceValue--summary"
        self.base_url = "https://www.drsimi.cl" 

    async def extraer_por_catalogo(self,url):
        # Contador de páginas en el sitio web
        num_pagina = 1
        # Lista para almacenar todos los productos extraídos
        todos_los_productos = []
        # Construcción de la URL por catalogos 
        url_catalogo = url
        # Ciclo para recorrer las páginas del catálogo y extraer nombre y precion de los productos
        while True:
            url_con_pagina = f"{url_catalogo}?page={num_pagina}"
            print(f"\n[DEBUG] Intentando cargar página {num_pagina}: {url_con_pagina}")
            
            try:
                # 1. Navegación con espera ligera
                await self.page.goto(url_con_pagina, wait_until="domcontentloaded", timeout=60000)
                
                # 2. ESPERA DE RENDERIZADO: Dr. Simi (VTEX) es pesado, esperamos a que aparezca un producto
                print(f"[DEBUG] Esperando a que aparezca el selector: {self.selector_producto}")
                try:
                    await self.page.wait_for_selector(self.selector_producto, timeout=10000)
                except:
                    print(f"[ERROR] El selector {self.selector_producto} no apareció tras 10s.")
                    # Lógica de auxilio: ¿Qué hay en la página?
                    html_snippet = await self.page.evaluate("() => document.body.innerHTML.substring(0, 500)")
                    print(f"[DEBUG] Inicio del HTML encontrado: {html_snippet}...")
                    break

                # 3. CONTEO DE PRODUCTOS
                nodos = await self.page.locator(self.selector_producto).all()
                print(f"[DEBUG] Productos encontrados en el DOM: {len(nodos)}")
                
                if not nodos:
                    print(f"[DEBUG] No hay más productos. Terminando en página {num_pagina}")
                    break

                # 4. EXTRACCIÓN DETALLADA
                for i, item in enumerate(nodos):
                    try:
                        nombre = await item.locator(self.selector_nombre).first.inner_text(timeout=3000)
                        precio = await item.locator(self.selector_precio).first.inner_text(timeout=3000)
                        
                        print(f"  [OK] Producto {i+1}: {nombre[:30]}... | {precio}")
                        
                        todos_los_productos.append({
                            "nombre": nombre.strip(),
                            "precio": precio.strip(),
                        })
                    except Exception as e:
                        print(f"  [!] Error en producto {i+1}: No pudo leer nombre o precio.")
                        # Opcional: imprimir el HTML del item fallido para ver qué cambió
                        continue

                num_pagina += 1
                await asyncio.sleep(random.uniform(1, 2))

            except Exception as e:
                print(f"[CRÍTICO] Error de navegación: {e}")
                break

        return todos_los_productos