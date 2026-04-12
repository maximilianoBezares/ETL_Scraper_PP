import asyncio
import os
from dotenv import load_dotenv
from ETL_Scraper.backend_client import OdooClient
from extract_to_filter.matcher import Matcher
from extract_to_filter.etl_matcher import ETLMatcher
from pages import knop
from playwright.async_api import async_playwright

async def main(): 
    load_dotenv()
    ODOO_CONFIG = {
        'url': os.getenv('ODOO_URL'),
        'db': os.getenv('ODOO_DB'),
        'user': os.getenv('ODOO_USER'),
        'api_key': os.getenv('ODOO_API_KEY')
    }
    print("Iniciando Sistema de Inteligencia de Precios")

    odoo = OdooClient(**ODOO_CONFIG)
    if not odoo.connect():
        print("No se pudo establecer conexión con Odoo. Abortando.")
        return
    print("Cargando configuración de catálogos desde Odoo...")
    pages_to_scrap = odoo.fetch_models()
    if not pages_to_scrap:
        print("⚠️ No se encontraron configuraciones de catálogos (URLs) en Odoo.")
        return
    #Configuramos la ETL
    etl = ETLMatcher(pages_to_scrap, odoo)
    print(f"Todo listo. Se procesarán {len(pages_to_scrap)} secciones de farmacias.")
    print("-" * 50)
    try:
        await etl.main_pipeling()
    except Exception as e:
        print(f"Error crítico durante la ejecución: {e}")
    finally:
        print("-" * 50)
        print("Proceso finalizado. Revisa Odoo y el Excel generado.")

if __name__ == "__main__":
    # Ejecutamos el loop asíncrono
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Proceso cancelado por el usuario.")
#--- IGNORE ---odoo.push_scraped_data('pharmacy.data.importer', all_products),}
"""if all_products and odoo.connect():
            print(all_products)"""