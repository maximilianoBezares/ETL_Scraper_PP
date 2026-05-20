import os
import requests
from dotenv import load_dotenv

# Cargamos las variables de tu .env
load_dotenv()

# Tomamos la URL que configuraste (http://host.docker.internal:5023)
base_url = os.getenv("API_BASE_URL") 
# Ajusta la ruta exacta si tu endpoint en .NET se llama diferente
login_url = f"{base_url}/api/auth/login" 

print(f"🚀 Iniciando prueba de conexión hacia: {login_url}")

try:
    # Enviamos un JSON con credenciales inventadas
    payload = {
        "email": "prueba_scraper@test.com", 
        "password": "password123"
    }
    
    # Hacemos la petición con un timeout de 5 segundos
    response = requests.post(login_url, json=payload, timeout=5)
    
    print("✅ ¡CONEXIÓN FÍSICA EXITOSA!")
    print(f"Código HTTP recibido: {response.status_code}")
    print(f"Respuesta de .NET: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ ERROR: No se pudo conectar (Connection Refused). El puente de red falló.")
except Exception as e:
    print(f"❌ ERROR INESPERADO: {e}")