import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from ETL_Scraper.pages.sodimac_page import AhumadaPage
from ETL_Scraper.pages.easy_page import CruzVerdePage
from pages.drsimi_page import DrsimiPage
from pages.knop import KnopPage
from pages.salcobrand_page import SalcobrandPage

class PharmacyScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.pharmacy_map = {
            "knop": KnopPage,
            "dr_simi": DrsimiPage,
            "ahumada": AhumadaPage,
            "salcobrand": SalcobrandPage,
            "cruz_verde": CruzVerdePage
        }
    async def start(self):
        """Inicia el navegador y el contexto"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        print("Navegador iniciado")
    async def stop(self):
        """Cierra todo para no dejar procesos colgando"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print(" Navegador cerrado")
    
    async def extract_data(self, url_pharmacy_tuple, id):
        url, pharmacy = url_pharmacy_tuple
        pharmacy_page = str(pharmacy) if pharmacy is not None else ""
        print(f"\n>>> Extrayendo: {pharmacy_page}...")

        if pharmacy_page.lower() not in self.pharmacy_map:
            print(f" Farmacia no reconocida: {pharmacy_page}")
            return []
        page = await self.context.new_page()

        class_instance = self.pharmacy_map[pharmacy_page.lower()](page)
        try: 
            resultados = await class_instance.extraer_por_catalogo(url)
            if resultados:
                df = pd.DataFrame(resultados)
                df['id_catalogo'] = id
                df['pharmacy'] = pharmacy_page  
                print(f"MUestra:{df.head(3)}")
                return df
            return None
    
        except Exception as e:
            print(f"Error al extraer datos de {pharmacy_page}: {e}")
            return None
        finally:
                #  cerramos la pestaña para liberar RAM, 
                # pero mantenemos el navegador abierto
            await page.close()