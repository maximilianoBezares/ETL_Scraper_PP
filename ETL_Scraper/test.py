import pandas as pd
from ETL_Scraper.backend_client import OdooClient # Ajusta la ruta a tu carpeta

def test_sync():
    # 1. Configuración (Usa tus credenciales reales)
    URL = "https://farmaciasgalenochile-practica-27306225.dev.odoo.com"
    DB = "farmaciasgalenochile-practica-27306225"
    USER = "admin"  
    API_KEY = "c48d1121125f7672b7dbf684ef610a111924e2f5" 
    
    odoo = OdooClient(URL, DB, USER, API_KEY)
    
    if not odoo.connect():
        print("❌ Falló la conexión inicial.")
        return

    print("🛠️ Creando datos de prueba simulados...")
    # Simulamos lo que el Matcher entregaría
    data = {
        'odoo_id': [1],  # <-- ASEGÚRATE de usar un ID de producto que exista en tu Odoo
        'nombre': ['Ibuprofeno 400mg Test'],
        'precio': ['$4.500'],
        'pharmacy': ['Farmacia Test'],
        'id_catalogo': [99],
        'status': ['matched']
    }
    df_test = pd.DataFrame(data)

    # 2. Intentar la subida
    print("🚀 Iniciando subida de prueba...")
    try:
        # Probamos el método que conecta todo
        odoo.push_scraped_data('product.pharmaceutical.price', df_test)
        print("✅ Prueba finalizada. Revisa en Odoo si el registro apareció.")
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")

if __name__ == "__main__":
    test_sync()