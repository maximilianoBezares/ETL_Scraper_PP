
import asyncio
from extract_to_filter.matcher import Matcher
from extract_to_filter.scraper import PharmacyScraper
from datetime import datetime
import pandas as pd

class ETLMatcher:
    def __init__(self, pages_to_scrap, odoo_instance):
        self.pages_to_scrap = pages_to_scrap
        self.odoo_instance = odoo_instance
        self.matcher = Matcher()

    async def main_pipeling(self):
        pharmacy_scraper = PharmacyScraper()
        await pharmacy_scraper.start()
        self.reporte_final = [] # Inicializar lista para el Excel

        try:   
            for (url, pharmacy), cat_id in self.pages_to_scrap.items():
                df_farmacia = await pharmacy_scraper.extract_data((url, pharmacy), cat_id)
                
                if df_farmacia is not None and not df_farmacia.empty:
                    # Traemos data de Odoo para comparar
                    df_odoo = self.odoo_instance.fetch_existing_products(cat_id)
                    
                    if df_odoo is not None and not df_odoo.empty:
                        # MATCHING
                        df_matched = self.matcher.run_pipeline(df_farmacia, df_odoo)

                        # SEPARAR EXITOSOS
                        # Usamos 'matched' y 'suspicious' según tu lógica
                        df_successful = df_matched[df_matched['status'].isin(['matched', 'suspicious'])]
                        
                        if not df_successful.empty:
                            # Conectar y enviar (El Singleton mantiene la sesión)
                            if self.odoo_instance.connect():
                                self.odoo_instance.push_scraped_data('product.pharmaceutical.price', df_successful)
                        
                        print(f"📊 {pharmacy}: {len(df_successful)} enviados, {len(df_matched[df_matched['status']=='fail'])} fallidos.")
                    else:
                        print(f"⚠️ Sin productos en Odoo para cat {cat_id}")
                else:
                    print(f"❌ Sin data extraída de {pharmacy}")

        except Exception as e:
            print(f"Error en el pipeline ETL: {e}")        
        finally:
            await pharmacy_scraper.stop()

def generar_reporte_excel(self):
        if not self.reporte_final:
            print("📭 No hay datos para generar el reporte.")
            return

        df_completo = pd.concat(self.reporte_final, ignore_index=True)
        fecha = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"Reporte_Matching_{fecha}.xlsx"

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Pestaña 1: Revisión (status 'suspicious')
            df_completo[df_completo['status'] == 'suspicious'].to_excel(writer, sheet_name='Para Revisar', index=False)
            # Pestaña 2: Fallidos (status 'fail')
            df_completo[df_completo['status'] == 'fail'].to_excel(writer, sheet_name='Sin Coincidencias', index=False)
            # Pestaña 3: Exitosos (status 'matched')
            df_completo[df_completo['status'] == 'matched'].to_excel(writer, sheet_name='Subidos a Odoo', index=False)

        print(f"📑 Excel generado: {filename}")