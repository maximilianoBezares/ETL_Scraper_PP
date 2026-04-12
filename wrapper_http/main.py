from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Response
from wrapper_http.launcher import validate_lock, launch_subprocess
import os
import json

app = FastAPI()

#Endpoint POST para realizar las validaciones del token de servicio, archivo.lock y runear el scraper
@app.post("/run-scraper")
async def run_scraper(response: Response, background_tasks: BackgroundTasks, x_service_token: str = Header(...)):
    token_real = os.getenv("SERVICE_TOKEN")
    if not token_real:
        raise HTTPException(status_code=500, detail="Error de configuracion en .env, SERVICE_TOKEN no definido correctamente")
    if x_service_token != token_real:
        raise HTTPException(status_code=401, detail="Token invalido")
    if validate_lock() == False:
        raise HTTPException(status_code=409, detail="Ya hay un scraper corriendo")
    else:
        background_tasks.add_task(launch_subprocess)
        response.status_code=202
        return {
            "status": "accepted",
            "message": "Scraper iniciado en segundo plano"
        }

#Endpoint GET para verificar el estado e informacion basica del scraper 
@app.get("/status")
async def get_status(response: Response, ):
    if os.path.exists("scraper.lock"):
        try:
            lock = open("scraper.lock", "r")
            if lock:
                info = json.load(lock)
                lock.close()
            pid = info.get("pid")
            if pid is None:
                response.status_code=200
                return {
                    "running": True,
                    "status": "Iniciando...",
                    "pid": None,
                    "inicio": info.get("inicio")
                }
            try:
                os.kill(pid,0)
                response.status_code = 200
                return {
                    "running": True,
                    "pid": pid,
                    "inicio": info.get("inicio"),
                    "creador": info.get("creador")
                }
            except OSError:
                print(f"El proceso murio pero el .lock sigue vivo: {pid}")
                try:
                    os.remove("scraper.lock")
                except:
                    pass
                response.status_code=202
                return {
                    "running": False,
                    "message": "El proceso murió inesperadamente. Lock limpiado."
            }
        except Exception:
            try:
                os.remove("scraper.lock")
            except:
                pass
            raise HTTPException(status_code=500, detail="Estado corrupto del lock")
    else:
        response.status_code=202
        return {
            "running": False,
            "message": "No hay scraper en ejecucion"
        }

#Endpoint POST para dropear el scraper en caso de emergencia
@app.post("/drop")    
async def drop_scraper(response: Response, x_service_token: str = Header(...)):
    token_real = os.getenv("SERVICE_TOKEN")
    if not token_real:
        raise HTTPException(status_code=500, detail="Error de configuracion en .env, SERVICE_TOKEN no definido correctamente")
    if x_service_token != token_real:
        raise HTTPException(status_code=401, detail="Token invalido")
    if os.path.exists("scraper.lock"):
        try:
            lock = open("scraper.lock")
            pid = None
            if lock:
                try:
                    info = json.load(lock)
                    pid = info.get("pid")
                except:
                    pass
                lock.close()
                if pid is not None:
                    try:
                        os.kill(pid,9)
                    except OSError:
                        pass
                try:
                    os.remove("scraper.lock")
                except FileNotFoundError:
                    pass
                response.status_code=200
                return {
                    "status": "killed",
                    "pid": pid
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        response.status_code=409
        return {
            "status": "not running"
        }