"""
main.py: Orquestador principal o punto de partida principal del microservicio ETL de scraping.

Responsable de inicializar el entorno (credenciales en .env), configurar el logging global,
establecer conexión con la API de .NET, obtener la configuración 
de los catálogos y orquestar la ejecución del pipeline principal.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from backend_client import BackendClient
from pipeline import Pipeline

async def main(): 
    load_dotenv()
    # 1. Carga las variables de entorno (.env) y crendeciales.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("main")
    # (Cambiar credenciales en .env en caso de ser necesario)
    BACKEND_CONFIG = {
        "base_url": os.getenv("API_BASE_URL"),
        "username":  os.getenv("API_USERNAME"),
        "password":  os.getenv("API_PASSWORD"),
    }
    logger.info("Iniciando Sistema de Extracción de Materiales de Construcción.")
    # 2. Autentica y conecta con el Backend .NET
    backend = BackendClient(**BACKEND_CONFIG)
    if not await backend.connect():
        logger.critical("No se pudo establecer conexión con el Backend .NET")
        return
    # 3. Solicita el diccionario de catálogos y URLs a procesar
    logger.info("Cargando configuración de catálogos desde el Backend .NET...")
    config_cruda = await backend.fetch_config()
    if not config_cruda:
        logger.warning("No se encontraron configuraciones de catálogos (URLs) en el Backend .NET.")
        return
    # Transformar lista JSON → formato que exige Pipeline
    # NOTA: ajustar nombres de campos cuando .NET confirme el esquema exacto
    pages_to_scrap = {
        (item["url"], item["supplierName"]): item["categoriaId"]
        for item in config_cruda
    }
    # 4. Instancia y ejecuta el Pipeline de extracción ETL
    etl = Pipeline(pages_to_scrap, backend)
    logger.info("Todo listo. Se procesarán %d secciones de Sodimac.", len(pages_to_scrap))
    logger.info("-" * 50)
    try:
        await etl.main_pipeling()
    except Exception as e:
        logger.exception("Error crítico durante la ejecución: %s", e)
    finally:
        logger.info("-" * 50)
        logger.info("Proceso finalizado. Revisa el Backend .NET y el Excel generado.")

if __name__ == "__main__":
    # Ejecutamos el loop asíncrono
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Proceso cancelado por el usuario.")