import asyncio as asyn
import random
import re
from .base_page import BasePage

class AhumadaPage(BasePage):
    def __init__(self, page):
        super().__init__(page, "Ahumada")
        self.selector_boton = "button.more"
        self.selector_producto = ".product-tile" 
        self.selector_nombre = ".pdp-link a.link"
        # Selector de precio mejorado para capturar el valor numérico real
        self.selector_precio = ".price .value" 
        self.selector_contenedor_precios = ".price"

    async def extraer_por_catalogo(self, url):
        print(f"Navegando a Ahumada: {url}...")
        await self.page.goto(url, wait_until="networkidle", timeout=60000)
        
        # 1. Expandimos todo el catálogo antes de extraer
        await self.cargar_todo_el_catalogo()
        
        self.logger.info("Iniciando extracción por ráfaga...")
        products = []
        
        # Contamos cuántos hay realmente
        locator_productos = self.page.locator(self.selector_producto)
        total = await locator_productos.count()
        
        # En lugar del bucle que tenías, usa este:
        for i in range(total):
            try:
                # 'evaluate' es la clave: extrae directamente del DOM de Chrome
                # sin las esperas automáticas de Playwright que causan el Timeout
                data = await locator_productos.nth(i).evaluate("""(node) => {
                    const nameEl = node.querySelector('.pdp-link a.link');
                    const priceEl = node.querySelector('.price .value');
                    return {
                        nombre: nameEl ? nameEl.innerText.trim() : '',
                        precio: priceEl ? priceEl.innerText.trim() : '0'
                    };
                }""")
                
                if data['nombre']:
                    products.append({
                        "nombre": data['nombre'],
                        "precio": data['precio'],
                        "pharmacy": "ahumada",
                        "id_catalogo": 8 # Asegúrate de pasar el ID aquí
                    })
            except Exception:
                continue
            
    async def cargar_todo_el_catalogo(self):
        self.logger.info("Iniciando expansión del catálogo de Ahumada...")    
        
        while True:
            # A. Scroll progresivo para encontrar el botón
            # Ahumada necesita que el botón esté en el viewport para activarse
            for _ in range(3):
                await self.page.mouse.wheel(0, 1000)
                await self.page.wait_for_timeout(800)

            boton = self.page.locator(self.selector_boton).first

            if await boton.is_visible():
                cantidad_antes = await self.page.locator(self.selector_producto).count()
                self.logger.info(f"Clic en 'Ver más'. Productos actuales: {cantidad_antes}")
                
                try:
                    await boton.scroll_into_view_if_needed()
                    await boton.click(force=True)
                    
                    # B. GUARDIÁN: Esperamos a que la cantidad aumente
                    # Usamos una función de JS para verificar el conteo en el navegador
                    await self.page.wait_for_function(
                        f"document.querySelectorAll('{self.selector_producto}').length > {cantidad_antes}",
                        timeout=15000
                    )
                    
                    # Pausa aleatoria para evitar detección de bot
                    await self.page.wait_for_timeout(random.randint(2000, 4000))
                    
                except Exception as e:
                    self.logger.warning("No se detectaron más productos tras el clic o carga lenta.")
                    break
            else:
                # Si el botón ya no es visible después de scrollear, terminamos
                self.logger.info("Se ha llegado al final del catálogo de Ahumada.")
                break