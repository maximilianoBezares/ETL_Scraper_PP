"""
pipeline.py: Módulo Orquestador del proceso ETL (Extract, Transform, Load).

Este archivo define la clase `Pipeline`, la cual es responsable de coordinar
a todos los actores del sistema: extraer los datos usando Playwright (`SupplierScraper`),
limpiar y estandarizar los textos usando Regex (`MaterialCleaner`), y enviar 
la carga final a la API mediante el cliente HTTP (`BackendClient`).
"""

import asyncio
import logging
from extraction_pipeline.cleaner import MaterialCleaner
from extraction_pipeline.scraper import SupplierScraper
from datetime import datetime
import pandas as pd
logger = logging.getLogger("pipeline")

class Pipeline:
    # Iniciamos todas las instancias a utilizar
    def __init__(self, pages_to_scrap, backend_instance):
        self.pages_to_scrap = pages_to_scrap
        self.backend_instance = backend_instance
        self.cleaner = MaterialCleaner()
        self._reporte_final: list[pd.DataFrame] = []

    # Ejecuta el ciclo completo ETL: conexión → extracción → limpieza → sincronización → reporte
    async def main_pipeling(self):
        # 1. Valida la conexión con el Backend con funcion connect()
        logger.info("Iniciando conexion con Backend...")
        if not await self.backend_instance.connect():
            logger.critical("No se pudo conectar al backend .NET. Abortando pipeline")           
            return
        # 2. Inicializa el motor de scraping (Playwright).
        supplier_scraper = SupplierScraper(self.backend_instance)
        await supplier_scraper.start()
        # Inicializar lista para el Excel
        self._reporte_final = []
        try:
            # 3. Itera sobre cada URL proporcionada y extrae la data cruda.
            for (url, supplier), cat_id in self.pages_to_scrap.items():
                logger.info("Procesando proveedor '%s' | URL: %s", supplier, url)
                df_proveedor = await supplier_scraper.extract_data((url, supplier), cat_id)
                if df_proveedor is not None and not df_proveedor.empty:
                    # 4. Envía la data cruda al `MaterialCleaner` para limpieza y extracción Regex.
                    df_cleaned = self.cleaner.procesar_dataframe(df_proveedor)
                    if not df_cleaned.empty:
                        logger.info("Enviando lote de %s al backend...", supplier)
                        self._reporte_final.append(df_cleaned)
                        # 5. Sincroniza (POST) los datos limpios por lotes hacia la API de .NET.
                        resumen = await self.backend_instance.sync_materiales(df_cleaned)
                        logger.info("'%s' sincronizado — Exitosos: %d | Fallidos: %d", supplier, resumen.total_exitosos, resumen.total_fallidos, )
                else:
                    logger.warning("Sin data extraída de %s", supplier)
        except Exception as e:
            logger.exception("Error crítico en el pipeline ETL: %s", e) 
        # 6. En caso de error o éxito, asegura el cierre del navegador (finally).     
        finally:
            await supplier_scraper.stop()