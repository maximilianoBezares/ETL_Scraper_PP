import asyncio
import pandas as pd
from extraction_pipeline.scraper import SupplierScraper

URL      = "https://www.sodimac.cl/sodimac-cl/lista/cat18320016/Maquinarias-y-complementos?page=1&store=so_com"
PROVEEDOR = "sodimac"
ID_FALSO  = 999

async def test_scraper_aislado():
    scraper = SupplierScraper()
    await scraper.start()
    try:
        df_resultado = await scraper.extract_data((URL, PROVEEDOR), ID_FALSO)
        if df_resultado is not None and not df_resultado.empty:
            print(df_resultado)
            df_resultado.to_excel("Test_Sodimac_Maquinarias.xlsx", index=False)
            print("✅ Extracción exitosa. Archivo guardado: Test_Sodimac_Maquinarias.xlsx")
        else:
            print("❌ La extracción retornó vacío o None. Revisa los selectores de SodimacPage.")
    except Exception as e:
        print(f"❌ Error durante la extracción: {e}")
    finally:
        await scraper.stop()

if __name__ == "__main__":
    asyncio.run(test_scraper_aislado())