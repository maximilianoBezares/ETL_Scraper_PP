import subprocess
import time
import os
import json
import datetime

#Funcion para lanzar el proceso del scraper de manera no bloqueante o en segundo plano
def launch_subprocess():
    status = None
    try:
        #Subproceso en segundo plano
        subproceso = subprocess.Popen(
            ["python", "main.py"],
            cwd="/app/scraper",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True)
        lock = open("scraper.lock", "w")
        if lock:
            info = {
                "pid": subproceso.pid,
            }
            lock.write(json.dumps(info))
            lock.close()
        #Monitoreo general
        print("Subproceso iniciado.")
        start_time = time.time()
        timeout = 172800
        while True:
            if time.time() - start_time > timeout:
                subproceso.kill()
                print("Proceso abortado por timeout de 2 horas")
                status = 'TIMEOUT'
                break
            status = subproceso.poll()
            stdout = subproceso.stdout.readline()
            if stdout == '' and status is not None:
                break
            if stdout:
                print(f"el proceso se sigue ejecutando: {stdout.strip()}")
                time.sleep(0.1)
    except Exception as e:
        print(f"Error al iniciar el subproceso: {e}")
    finally:
        #Borrado de archivo .lock al terminar el proceso
        drop_lock()
        if status == 0:
            print(f"el proceso ha finalizado con exito, Exit code: {status}")
        elif status == 'TIMEOUT':
            print("Proceso abortado por timeout")
        else:
            print(f"El proceso a finalizado con errores, Exit code: {status}")

#Verificacion de archivo .lock 
def validate_lock():
    try:
        lock = open("scraper.lock", "x") 
        info = {
            "pid": None,
            "inicio": str(datetime.datetime.now()),
            "creador": "Launcher"
        }
        lock.write(json.dumps(info))
        lock.close()
        return True
    except FileExistsError:
        print("Scraper ya existe")
        return False

#Borrado de archivo .lock    
def drop_lock():
    try:
        os.remove("scraper.lock")
        print()
    except FileNotFoundError:
        pass