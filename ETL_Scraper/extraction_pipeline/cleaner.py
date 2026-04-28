"""
cleaner.py: limpieza y parseo de datos.

recibie datos crudos extraídos de la web y los
devuelve limpios, normalizados y enriquecidos con especificaciones
técnicas parseadas via Regex, listos para ser enviados por BackendClient.
"""

from __future__ import annotations
import logging
import re
import unicodedata
from typing import Any
import pandas as pd
logger = logging.getLogger("material_cleaner")

class MaterialCleaner:
    # Diferentes patrones REGEX para traducir antes de la ejecucion:

    # Grosor / Espesor
    _RE_GROSOR = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(mm|cm|pulgadas|pulg)",
        re.IGNORECASE,
    )

    # Dimensiones en formato Ancho x Alto (área/superficie)
    _RE_DIMENSIONES = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*(mt?|cm|mm|metros?)",
        re.IGNORECASE,
    )

    # Peso
    _RE_PESO = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(kg|kilos?|gr|gramos?)",
        re.IGNORECASE,
    )

    # Largo / Longitud simple (sin "x", solo una dimensión lineal)
    _RE_LARGO = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(mt?|metros?|cms?)",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        logger.info(
            "MaterialCleaner inicializado. "
            "Modo: limpieza de texto + parseo Regex."
        )

    def limpiar_texto(self, texto: Any) -> str:
        if not texto:
            return ""
        sin_tildes = "".join(
            c for c in unicodedata.normalize("NFD", str(texto))
            if unicodedata.category(c) != "Mn"
        )
        solo_alfanum = re.sub(r"[^a-z0-9 ]", " ", sin_tildes.lower())
        return " ".join(solo_alfanum.split())

    def limpiar_precio(self, texto_precio: Any) -> int:
        if not texto_precio:
            return 0
        if isinstance(texto_precio, (int, float)):
            return int(texto_precio)
        limpio = re.sub(r"[^\d]", "", str(texto_precio))
        try:
            return int(limpio)
        except ValueError:
            return 0

    # El diccionario resultante es heterogéneo por diseño: distintos materiales tienen distintas propiedades
    def extraer_especificaciones(self, nombre_limpio: str) -> dict[str, str]:
        especificaciones: dict[str, str] = {}
        # Grosor / Espesor
        match_grosor = self._RE_GROSOR.search(nombre_limpio)
        if match_grosor:
            valor = match_grosor.group(1).replace(",", ".")
            unidad = match_grosor.group(2).lower()
            especificaciones["grosor"] = f"{valor}{unidad}"
        # Dimensiones (Ancho x Largo)
        match_dim = self._RE_DIMENSIONES.search(nombre_limpio)
        if match_dim:
            ancho = match_dim.group(1).replace(",", ".")
            largo = match_dim.group(2).replace(",", ".")
            unidad = match_dim.group(3).lower()
            especificaciones["dimensiones"] = f"{ancho}x{largo}{unidad}"
        # Largo lineal — solo si no se capturó ya con dimensiones
        if "dimensiones" not in especificaciones:
            match_largo = self._RE_LARGO.search(nombre_limpio)
            if match_largo:
                valor = match_largo.group(1).replace(",", ".")
                unidad = match_largo.group(2).lower()
                especificaciones["largo"] = f"{valor}{unidad}"
        # Peso
        match_peso = self._RE_PESO.search(nombre_limpio)
        if match_peso:
            valor = match_peso.group(1).replace(",", ".")
            unidad = match_peso.group(2).lower()
            especificaciones["peso"] = f"{valor}{unidad}"

        return especificaciones

    # Pipeline completo de limpieza sobre un DataFrame scrapeado.
    def procesar_dataframe(self, df_crudo: pd.DataFrame) -> pd.DataFrame:
        if df_crudo.empty:
            logger.warning("procesar_dataframe() recibió un DataFrame vacío.")
            return df_crudo
        # Creacion de una copia
        df = df_crudo.copy()
        nombres_limpios: list[str] = []
        precios_limpios: list[int] = []
        atributos_lista: list[dict[str, str]] = []
        for idx, row in df.iterrows():
            try:
                nombre_limpio = self.limpiar_texto(row.get("nombre", ""))
                precio_limpio = self.limpiar_precio(row.get("precio", 0))
                atributos = self.extraer_especificaciones(nombre_limpio)
            except Exception as exc:
                logger.warning(
                    "Error procesando fila %s: %s "
                    "Se asignan valores por defecto.", idx, exc
                )
                nombre_limpio = ""
                precio_limpio = 0
                atributos = {}
            nombres_limpios.append(nombre_limpio)
            precios_limpios.append(precio_limpio)
            atributos_lista.append(atributos)
        df["nombre_limpio"] = nombres_limpios
        df["precio"] = precios_limpios
        df["atributos_tecnicos"] = atributos_lista
        logger.info(
            "procesar_dataframe() completado: %d filas procesadas "
            "Columnas resultantes: %s",
            len(df),
            list(df.columns),
        )
        return df