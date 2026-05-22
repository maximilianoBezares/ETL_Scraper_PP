"""
backend_client.py

Cliente HTTP para comunicar el microservicio de scraping (Python/FastAPI)
con el backend principal (.NET Core 10).
"""

from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any
import httpx
import pandas as pd

logger = logging.getLogger("backend_client")

# Modelos de datos | Uso de DTOs

#DTO en representacion de un material de construccion
@dataclass
class MaterialScraped:
    nombre: str
    precio: int
    marca: str
    proveedor: str
    imagen_url: str
    # Con default_factory=dict es para crear diccionarios especificos para cada atributo, en vez de una lista con tamaño estatico
    atributos_tecnicos: dict[str, str] = field(default_factory=dict)
    # Posibles atributos opcionales
    url_material: str = ""
    categoria: str = ""

    # Funcion que toma el objeto de python y lo convierte en un diccionario crudo con el esquema esperado por .NET
    def to_api_dict(self):
        return {
            "nombre": self.nombre,
            "precio": self.precio,
            "marca": self.marca,
            "proveedor": self.proveedor,
            "imagenUrl": self.imagen_url,
            "urlMaterial": self.url_material,
            "categoria": self.categoria,
            "atributosTecnicos": self.atributos_tecnicos
        }

#DTO en representacion de un sumario de una ejecucion de sync_materiales() para panel de control
@dataclass
class SumarioResultados:
    ejecucion_id: str = ""
    total_procesados: int = 0
    total_exitosos: int = 0
    total_fallidos: int = 0
    # Con default_factory=dict es para crear diccionarios especificos para cada atributo, en vez de una lista con tamaño estatico
    categorias_fallidas: list[str] = field(default_factory=list)
    errores_detalle: list[dict[str, Any]] = field(default_factory=list)

    # Funcion que toma el objeto de python y lo convierte en un diccionario crudo con el esquema esperado por .NET
    def to_dict(self):
        data = {
            "totalProcesados": self.total_procesados,
            "totalExitosos": self.total_exitosos,
            "totalFallidos": self.total_fallidos,
            "categoriasFallidas": self.categorias_fallidas,
            "erroresDetalle": self.errores_detalle,
        }
        if self.ejecucion_id and str(self.ejecucion_id).strip():
            data["ejecucionId"] = self.ejecucion_id
        return data

# Cliente HTTP Singleton para el backend .NET
class BackendClient:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self,
        base_url = None,
        email = None,
        password = None,
        timeout = 30.0,
        max_retries = 3,
        batch_size = 50,
    ):
        # Solo inicializamos la primera vez
        if self._initialized:
            return
        self.base_url = (base_url or "").rstrip("/")
        self.username = email or ""
        self.password = password or ""
        self.timeout = timeout
        self.max_retries = max_retries
        self.batch_size = batch_size
        # Estado interno
        self._jwt_token = None
        self._http_client = None
        self._initialized = True

    # Funcion para utilizar una unica conexion para los 50 batches y no 50 conexiones para cada 50 batches
    def _get_client(self):
        if self._http_client is None or self._http_client.is_closed:
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            if self._jwt_token:
                headers["Authorization"] = f"Bearer {self._jwt_token}"
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._http_client

    # Funcion para actualizar los Header: cuando un cliente activo se le actualice su JWT y no se le cree otro
    def _inject_auth_header(self):
        if self._http_client and self._jwt_token:
            self._http_client.headers["Authorization"] = f"Bearer {self._jwt_token}"

    # Funcion que cierra de forma segura el AsyncClient y libera todas las conexiones de red que estaban abiertas
    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # Autentica el microservicio contra el backend .NET y almacena el JWT.
    async def connect(self):
        # Si ya tenemos token vigente, no perdemos el tiempo reautenticando
        if self._jwt_token:
            logger.info("Ya hay una sesión JWT activa")
            return True
        client = self._get_client()
        credenciales = {"email": self.username, "password": self.password}
        try:
            # Cambiar /api/auth/login si es que ruta es distinta a la del login
            response = await client.post("/api/auth/login", json=credenciales)
            if response.status_code == 200:
                data = response.json()
                self._jwt_token = data.get("token")
                # Validacion si es que token no es el nombre de la clave
                if not self._jwt_token:
                    logger.error("El backend no retornó un token en la respuesta")
                    return False
                self._inject_auth_header()
                logger.info("Autenticación exitosa. JWT almacenado en memoria")
                return True
            elif response.status_code == 401:
                logger.error("Credenciales de servicio inválidas")
            else:
                logger.error(
                    "Error inesperado al autenticar "
                    "Status: %s — %s", response.status_code, response.text
                )
            return False
        except httpx.ConnectError:
            logger.critical(
                "No se pudo conectar al backend en %s. "
                "Verifica que el servicio .NET esté corriendo", self.base_url
            )
            return False
        except httpx.TimeoutException:
            logger.error("Timeout al intentar autenticar contra el backend")
            return False
        except Exception as exc:
            logger.exception("Error desconocido en connect(): %s", exc)
            return False

    # Obtiene la lista de URLs y categorías de construcción que el scraper
    async def fetch_config(self):
        if not self._jwt_token:
            logger.error("fetch_config() llamado sin JWT. Ejecuta connect() primero")
            return []
        client = self._get_client()
        try:
            response = await client.get("/api/scraper/config")
            if response.status_code == 200:
                config = response.json()
                logger.info(
                    "Configuración recibida: %d categorías/URLs a procesar",
                    len(config),
                )
                return config
            elif response.status_code == 401:
                logger.error("Token expirado o inválido al llamar fetch_config(). Reautentica")
            else:
                logger.error(
                    "fetch_config() falló. Status: %s — %s",
                    response.status_code, response.text
                )
            return []
        except httpx.TimeoutException:
            logger.error("Timeout al obtener configuración del backend")
            return []
        except Exception as exc:
            logger.exception("Error inesperado en fetch_config(): %s", exc)
            return []

    # Envía los productos scrapeados al backend .NET en lotes de `batch_size`
    async def sync_materiales(self, df_scrapeado):
        if not self._jwt_token:
            logger.error("sync_materiales() llamado sin JWT. Ejecuta connect() primero")
            return SumarioResultados()
        if df_scrapeado.empty:
            logger.warning("El DataFrame está vacío. No hay productos para sincronizar")
            return SumarioResultados()
        # Construir lista de diccionarios listos para la API
        materiales_api: list[dict[str, Any]] = []
        for _, row in df_scrapeado.iterrows():
            try:
                print(f"DEBUG: columnas disponibles: {df_scrapeado.columns.tolist()}")
                print(f"DEBUG: primer valor de id_catalogo: {df_scrapeado['id_catalogo'].iloc[0]}")
                producto = MaterialScraped(
                    nombre=str(row.get("nombre", "")),
                    precio=self._limpiar_precio(row.get("precio", 0)),
                    marca=str(row.get("marca", "Sin marca")),
                    proveedor=str(row.get("proveedor", "Desconocido")),
                    imagen_url=str(row.get("imagen_url", "")),
                    atributos_tecnicos=row.get("atributos_tecnicos") or {},
                    url_material=str(row.get("url_producto", "")),
                    categoria=str(row.get("id_catalogo", "")),
                )
                materiales_api.append(producto.to_api_dict())
            except Exception as exc:
                logger.warning("Fila ignorada por error de mapeo: %s", exc)
        summary = SumarioResultados(total_procesados=len(materiales_api))
        client = self._get_client()
        logger.info(
            "Iniciando sincronización: %d productos en lotes de %d",
            len(materiales_api), self.batch_size
        )
        # Procesar lotes utilizando algoritmo de chunking (de 50 en 50)
        for i in range(0, len(materiales_api), self.batch_size):
            lote = materiales_api[i : i + self.batch_size]
            lote_num = (i // self.batch_size) + 1
            ids_lote = [p["nombre"] for p in lote]
            exito = await self._enviar_lote_con_reintentos(
                client=client,
                lote=lote,
                lote_num=lote_num,
                ids_lote=ids_lote,
                summary=summary,
            )
            if exito:
                summary.total_exitosos += len(lote)
            else:
                summary.total_fallidos += len(lote)
        logger.info(
            "Sincronización finalizada — Procesados: %d | Exitosos: %d | Fallidos: %d",
            summary.total_procesados,
            summary.total_exitosos,
            summary.total_fallidos,
        )
        # Enviar resumen al backend para el panel de administracion
        await self._enviar_resumen(client, summary)
        return summary

    # Intenta enviar un lote hasta max_retries veces con exponential backoff.
    async def _enviar_lote_con_reintentos(self, client, lote, lote_num, ids_lote, summary):
        for intento in range(1, self.max_retries + 1):
            try:
                # Cambiar endpoint si es que el nombre de la ruta no es el mismo
                response = await client.post(
                    "/api/scraper/productos/bulk",
                    json={"productos": lote},
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(
                        "Lote #%d enviado — Insertados: %s | Ignorados: %s",
                        lote_num,
                        data.get("insertados", len(lote)),
                        data.get("ignorados", 0),
                    )
                    return True
                # Error de cliente → no tiene sentido reintentar
                if 400 <= response.status_code < 500:
                    motivo = f"Error de cliente {response.status_code}: {response.text[:300]}"
                    logger.error("Lote #%d rechazado permanentemente. %s", lote_num, motivo)
                    summary.errores_detalle.append({
                        "lote": lote_num,
                        "motivo": motivo,
                        "productos_afectados": ids_lote,
                    })
                    return False
                # Error de servidor → reintentable
                logger.warning(
                    "Lote #%d — Intento %d/%d falló (status %s). Reintentando...",
                    lote_num, intento, self.max_retries, response.status_code,
                )
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                logger.warning(
                    "Lote #%d — Intento %d/%d error de red: %s. Reintentando...",
                    lote_num, intento, self.max_retries, exc,
                )
            except Exception as exc:
                logger.exception(
                    "Lote #%d — Error inesperado en intento %d: %s",
                    lote_num, intento, exc,
                )
            if intento < self.max_retries:
                espera = 2 ** intento
                logger.info("Esperando %ds antes del siguiente intento...", espera)
                await asyncio.sleep(espera)
        # Agoto los reintentos
        motivo = f"Agotó {self.max_retries} reintentos sin éxito."
        logger.error("Lote #%d — %s", lote_num, motivo)
        summary.errores_detalle.append({
            "lote": lote_num,
            "motivo": motivo,
            "productos_afectados": ids_lote,
        })
        return False

    # Envía el SumarioResultados al backend al finalizar toda la sincronización. 
    # El administrador lo verá en el panel de control (.NET).
    async def _enviar_resumen(self, client, summary):
        try:
            # Cambiar endpoint si es que el nombre de la ruta no es el mismo
            response = await client.post(
                "/api/scraper/resumen",
                json=summary.to_dict(),
            )
            if response.status_code in (200, 201):
                logger.info("Resumen de ejecución enviado al panel de administración")
            else:
                logger.warning(
                    "No se pudo enviar el resumen. Status: %s", response.status_code
                )
        except Exception as exc:
            logger.warning("Error al enviar resumen al backend: %s", exc)

    async def verificar_materiales_nuevos(self, urls: list[str]) -> list[str]:
        if not urls:
            return []
        client = self._get_client()
        try:
            # httpx serializa listas como ?urls=x&urls=y automáticamente
            response = await client.get(
                "/api/scraper/validate-batch",
                params=[("urls", url) for url in urls],
            )
            if response.status_code == 200:
                existentes = set(response.json().get("urlsExistentes", []))
                urls_nuevas = [url for url in urls if url not in existentes]
                logger.info("Pre-validación: %d enviadas | %d nuevas | %d ya existentes", len(urls), len(urls_nuevas), len(existentes),)
                return urls_nuevas
            logger.error("validate-batch falló. Status: %s — %s", response.status_code, response.text)
            return urls
        except Exception as exc:
            logger.exception("Error en verificar_materiales_nuevos: %s", exc)
            return urls

    @staticmethod
    # Convierte un precio en texto a entero (pesos chilenos)
    def _limpiar_precio(texto_precio):
        if not texto_precio:
            return 0
        import re
        limpio = re.sub(r"[^\d]", "", str(texto_precio))
        try:
            return int(limpio)
        except ValueError:
            return 0