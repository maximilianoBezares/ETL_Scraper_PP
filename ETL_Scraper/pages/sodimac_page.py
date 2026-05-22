import asyncio as asyn
from .base_page import BasePage

class SodimacPage(BasePage):
    def __init__(self, page, backend_instance):
        super().__init__(page, "Sodimac")
        self.backend_instance = backend_instance
        # Selectores especiales de Sodimac
        self.selector_boton_next = "button#testId-pagination-bottom-arrow-right"
        self.selector_material = "div.search-results-4-grid.grid-pod"
        self.selector_nombre = "b.pod-subTitle"
        self.selector_marca = "b.pod-title"
        self.selector_proveedor = "b.pod-sellerText"
        self.selector_precio = "li[data-internet-price] span, li[data-event-price] span"
        self.selector_link = "a"
        self.selector_imagen = "img"
        self.selector_descripcion = "div.fb-product-information-tab__copy"

    # Funcion general para todas las paginas
    async def extraer_por_catalogo(self, url):
        self.logger.info("Navegando a Sodimac Catalogo: %s...", url)
        await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        materiales = []
        num_pagina  = 1
        while True:
            self.logger.info("Procesando página %d...", num_pagina)
            # 1. Volver al tope (evita cursor fantasma tras paginación)
            await self.page.evaluate("window.scrollTo(0, 0);")
            await self.page.wait_for_timeout(800)
            # 2. Cerrar popups antes de scrollear
            await self.manejar_popups_emergentes()
            # 3. Scroll progresivo
            await self._scroll_progresivo()
            # 4. Extraer productos de esta página
            materiales_pagina = await self._extraer_materiales_pagina(num_pagina)
            # 5. Extraer descripcion solo a materiales nuevos (No estan en la base de datos)
            if materiales_pagina:
                urls_pagina = [m["url_producto"] for m in materiales_pagina]
                urls_nuevas_set = set(await self.backend_instance.verificar_materiales_nuevos(urls_pagina))
                for i in materiales_pagina:
                    link_actual = i["url_producto"]
                    if link_actual in urls_nuevas_set:
                        desc_material = await self._fetch_detalle(link_actual)
                        i["descripcion"] = desc_material
                        self.logger.info("Descripcion agregada a: " + i["nombre"])
            materiales.extend(materiales_pagina)
            self.logger.info("Página %d: %d materiales extraídos (total acumulado: %d).", num_pagina, len(materiales_pagina), len(materiales))
            # 6. Cambio de pagina usando boton_next
            boton_next = self.page.locator(self.selector_boton_next)
            if not await boton_next.is_visible():
                self.logger.info("No hay más páginas. Extracción finalizada.")
                break
            url_antes = self.page.url
            await boton_next.scroll_into_view_if_needed()
            await boton_next.evaluate("node => node.click()")
            self.logger.info("Click en 'siguiente'. Esperando cambio de URL...")
            # ignora productos patrocinados
            try:
                await self.page.wait_for_url(lambda url: url != url_antes,timeout=20000)
                num_pagina += 1
                self.logger.info("Cambio de URL detectado. Ahora en página %d.", num_pagina)
                # Espera breve para que React hidrate el nuevo contenido
                await self.page.wait_for_timeout(1500)
            except Exception:
                self.logger.warning("Timeout esperando cambio de URL en página %d. Finalizando.", num_pagina)
                break
        return materiales

    # Scroll dinámico y sensorial: evalúa el crecimiento del DOM (Estructura HTML de la pagina) para saber cuándo detenerse
    async def _scroll_progresivo(self):
        intentos_sin_crecimiento = 0
        intentos = 3
        max_ciclos = 30
        conteo_anterior = 0
        for i in range(max_ciclos):
            # Evita la sobrecarga del mouse
            await self.page.evaluate("window.scrollBy(0, 900);")
            await self.page.wait_for_timeout(500)
            conteo_actual = await self.page.locator(self.selector_material).count()
            # Si el DOM carga nuevos productos, el scroll funcionó
            if conteo_actual > conteo_anterior:
                intentos_sin_crecimiento = 0
                conteo_anterior = conteo_actual
            else:
                # Si se estanca por 3 ciclos, asumimos que llegamos al final real
                intentos_sin_crecimiento += 1
                if intentos_sin_crecimiento >= intentos:
                    break

    # Extracción masiva delegada al motor V8 de Chrome (Alta velocidad y tolerancia a fallos)
    async def _extraer_materiales_pagina(self, num_pagina):
        try:
            await self.page.wait_for_selector(self.selector_material, timeout=15000)
            materiales = await self.page.evaluate(
                """
                (selectores) => {
                    const items = document.querySelectorAll(selectores.material);
                    return Array.from(items).map(item => ({
                        nombre: item.querySelector(selectores.nombre)?.innerText.trim()         ?? "",
                        marca: item.querySelector(selectores.marca)?.innerText.trim()          ?? "",
                        precio: item.querySelector(selectores.precio)?.innerText.trim()         ?? "",
                        proveedor: item.querySelector(selectores.proveedor)?.innerText.trim()      ?? "",
                        url_producto: item.querySelector(selectores.link)?.getAttribute("href")       ?? "",
                        imagen_url: item.querySelector(selectores.imagen)?.getAttribute("src")      ?? "",
                    })).filter(p => p.nombre !== "");
                }
                """, {
                    "material": self.selector_material,
                    "nombre": self.selector_nombre,
                    "marca": self.selector_marca,
                    "precio": self.selector_precio,
                    "proveedor": self.selector_proveedor,
                    "link": self.selector_link,
                    "imagen": self.selector_imagen,
            })
            self.logger.info("Página %d: %d materiales extraídos.", num_pagina, len(materiales))
            return materiales
        except Exception as e:
            self.logger.error("Error al extraer materiales en pág %d: %s", num_pagina, e)
        return []
    
    # Funcion que extrae el detalle de un material tomando solo la descripcion
    async def _fetch_detalle(self, url_material):
        pagina_detalle = None
        try:
            pagina_detalle = await self.page.context.new_page()
            await pagina_detalle.goto(url_material, wait_until="domcontentloaded", timeout=30000)
            await pagina_detalle.wait_for_selector(self.selector_descripcion, timeout=10000)
            elemento = pagina_detalle.locator(self.selector_descripcion).first
            texto = await elemento.inner_text(timeout=5000)
            self.logger.info("Detalle obtenido para: %s", url_material)
            return texto
        except Exception as e:
            self.logger.error("Retornando vacio.", e)
            return ""
        finally:
            # Cerrar la pestaña para liberar RAM
            if pagina_detalle and not pagina_detalle.is_closed():
                await pagina_detalle.close()