"""
scraper.py: encargado de administrar el ciclo de vida del navegador (Playwright)
y enrutar la extracción de datos a las clases específicas de cada proveedor.

Implementa un patrón Factory a través de `supplier_map` para instanciar 
dinámicamente las clases correspondientes (ej. SodimacPage) y maneja las 
pestañas del navegador de forma aislada para evitar fugas de memoria.
"""

import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from pages.sodimac_page import SodimacPage

class SupplierScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.supplier_map = {
            "sodimac": SodimacPage,
        }
    
    # Enciende el motor de Playwright y lanza una instancia de Chromium
    async def start(self):
        # Inicia el navegador y el contexto
        self.playwright = await async_playwright().start()
        # Inicia Chromium
        self.browser = await self.playwright.chromium.launch(headless=True)
        # Inyecta un User-Agent realista para simular que es un humano navegando
        # desde Chrome en Windows, evitando bloqueos de seguridad básicos
        self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        print("Navegador iniciado")
    
    # Apaga el navegador y destruye el contexto de forma segura
    async def stop(self):
        # Cierra todo para no dejar procesos colgando
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("Navegador cerrado")
    
    # Abre una nueva pestaña, enruta la URL a la clase correspondiente y
    # extrae los datos, devolviéndolos en un formato tabular estandarizado
    async def extract_data(self, url_supplier_tuple, id):
        url, supplier = url_supplier_tuple
        supplier_page = str(supplier) if supplier is not None else ""
        print(f"\n>>> Extrayendo: {supplier_page}...")
        # Validación: Si el proveedor no está en el diccionario, abortamos la extracción
        if supplier_page.lower() not in self.supplier_map:
            print(f" Proveedor no reconocido: {supplier_page}")
            return []
        # Aislamiento: Creamos una pestaña totalmente nueva para esta extracción
        page = await self.context.new_page()
        # Patrón Factory: Instanciamos la clase dinámicamente según el proveedor
        class_instance = self.supplier_map[supplier_page.lower()](page)
        try:
            # Delegamos la lógica de navegación y extracción a la clase específica
            resultados = await class_instance.extraer_por_catalogo(url)
            if resultados:
                df = pd.DataFrame(resultados)
                df['id_catalogo'] = id
                df['proveedor'] = supplier_page  
                print(f"Muestra:{df.head(3)}")
                return df
            return None
        except Exception as e:
            print(f"Error al extraer datos de {supplier_page}: {e}")
            return None
        finally:
            # cerramos la pestaña para liberar RAM, pero mantenemos el navegador abierto
            await page.close()