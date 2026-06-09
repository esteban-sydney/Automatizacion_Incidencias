import asyncio
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import core.config as Config


class RemediAutomation:
    def __init__(self, log_callback=None):
        self.log = log_callback or print
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None

    async def iniciar(self):
        self.log("Iniciando navegador...")
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=Config.USER_DATA_DIR,
            channel=Config.BROWSER_CHANNEL,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        await self.page.goto(Config.REMEDI_URL, wait_until="networkidle", timeout=60000)
        await self._manejar_sso()
        await self._abrir_nueva_incidencia()

    async def _manejar_sso(self):
        if "login.microsoftonline" not in self.page.url and "login.live" not in self.page.url:
            return

        self.log("Esperando SSO...")
        await self.page.wait_for_url(f"**{Config.REMEDI_DOMAIN}**", timeout=30000)

    async def _abrir_nueva_incidencia(self):
        if Config.NUEVA_INCIDENCIA_URL:
            await self.page.goto(Config.NUEVA_INCIDENCIA_URL, wait_until="networkidle", timeout=30000)
            self.log("Formulario listo.")
            return

        await self.page.wait_for_load_state("networkidle", timeout=15000)
        await self.page.wait_for_timeout(2000)
        await self.page.click("a[title*='Mostrar lista de aplicaciones']", force=True)
        await self._click_texto_visible(Config.SELECTOR_MENU_GESTION, timeout=8000)
        await self._click_texto_visible(Config.SELECTOR_MENU_NUEVA, timeout=8000)
        await self.page.wait_for_load_state("networkidle", timeout=12000)
        await self.page.wait_for_timeout(1500)
        self.log("Formulario listo.")

    async def ingresar_parametros(self, datos: dict):
        titulo = self._crear_titulo(datos)

        await self._seleccionar_cliente(datos["cliente"])
        await self._llenar_por_etiqueta("Notas", titulo)
        await self._llenar_por_etiqueta("Resumen", titulo)
        self.log(f"Parametros ingresados: {titulo}")

    def _crear_titulo(self, datos: dict) -> str:
        partes = [
            datos["tipo"],
            f"entre {datos['origen']} y {datos['destino']}",
            "OSN 8800",
            f"Via {datos['via']}",
        ]
        return " ".join(parte for parte in partes if parte)

    async def _click_texto_visible(self, texto: str, timeout: int = 20000):
        deadline = asyncio.get_running_loop().time() + (timeout / 1000)

        while asyncio.get_running_loop().time() < deadline:
            for contexto in [self.page, *self.page.frames]:
                for candidato in (
                    contexto.get_by_role("link", name=texto, exact=True),
                    contexto.get_by_role("button", name=texto, exact=True),
                    contexto.get_by_role("menuitem", name=texto, exact=True),
                    contexto.get_by_text(texto, exact=False),
                ):
                    try:
                        total = min(await candidato.count(), 10)
                    except Exception:
                        continue

                    for indice in range(total):
                        elemento = candidato.nth(indice)
                        if not await elemento.is_visible(timeout=250):
                            continue

                        await elemento.scroll_into_view_if_needed(timeout=1500)
                        await elemento.click(timeout=2500)
                        return

            await self.page.wait_for_timeout(200)

        raise RuntimeError(f"No se encontró '{texto}'")

    async def _llenar_por_etiqueta(self, etiqueta: str, valor: str):
        campo = await self._campo_por_etiqueta(etiqueta)
        await campo.fill(valor, timeout=5000)

    async def _seleccionar_cliente(self, apellidos: str):
        apellidos = apellidos.strip().upper()
        campo = await self._campo_por_etiqueta("Cliente")
        await campo.click(timeout=5000)
        await self.page.keyboard.press("Control+A")
        await self.page.keyboard.press("Backspace")
        await self.page.wait_for_timeout(300)
        await self.page.keyboard.type(apellidos, delay=180)
        await self.page.wait_for_timeout(1200)
        await self._click_sugerencia_cliente(apellidos, campo)
        await self._validar_cliente_seleccionado(apellidos, campo)

    async def _click_sugerencia_cliente(self, texto: str, campo_cliente):
        deadline = asyncio.get_running_loop().time() + 8

        while asyncio.get_running_loop().time() < deadline:
            opcion = await self._buscar_sugerencia_cercana(texto, campo_cliente)
            if opcion:
                await opcion.click(timeout=3000)
                return

            await self.page.wait_for_timeout(200)

        raise RuntimeError(f"No apareció sugerencia para cliente '{texto}'")

    async def _validar_cliente_seleccionado(self, apellidos: str, campo_cliente):
        deadline = asyncio.get_running_loop().time() + 5
        palabras = [palabra for palabra in apellidos.upper().split() if palabra]

        while asyncio.get_running_loop().time() < deadline:
            valor = (await campo_cliente.input_value(timeout=1000)).strip().upper()
            if valor != apellidos and all(palabra in valor for palabra in palabras):
                return

            await self.page.wait_for_timeout(200)

        raise RuntimeError("Cliente no fue seleccionado desde la sugerencia")

    async def _buscar_sugerencia_cercana(self, texto: str, campo_cliente):
        box = await campo_cliente.bounding_box()
        if not box:
            return None

        texto = texto.strip().lower()
        for contexto in [self.page, *self.page.frames]:
            candidato = await contexto.evaluate_handle(
                """
                ({ texto, box }) => {
                    const visible = (el) => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return rect.width > 0 && rect.height > 0 &&
                            style.display !== "none" && style.visibility !== "hidden";
                    };

                    const normalizar = (valor) => (valor || "")
                        .replace(/\\s+/g, " ")
                        .trim()
                        .toLowerCase();

                    const opciones = [...document.querySelectorAll("div, span, td, li, a")]
                        .filter(visible)
                        .filter(el => normalizar(el.textContent).includes(texto))
                        .map(el => ({ el, rect: el.getBoundingClientRect() }))
                        .filter(item => item.rect.top >= box.y && item.rect.top <= box.y + 120)
                        .filter(item => item.rect.left >= box.x - 20 && item.rect.left <= box.x + box.width + 300)
                        .sort((a, b) => a.rect.top - b.rect.top || a.rect.left - b.rect.left);

                    return opciones.length ? opciones[0].el : null;
                }
                """,
                {"texto": texto, "box": box},
            )

            elemento = candidato.as_element()
            if elemento:
                return elemento

        return None

    async def _valor_por_etiqueta(self, etiqueta: str) -> str:
        campo = await self._campo_por_etiqueta(etiqueta)
        return (await campo.input_value(timeout=5000)).strip()

    async def _campo_por_etiqueta(self, etiqueta: str):
        for contexto in [self.page, *self.page.frames]:
            handle = await contexto.evaluate_handle(
                """
                (etiqueta) => {
                    const normalizar = (texto) => (texto || "")
                        .replace(/[*+:]/g, "")
                        .replace(/\\s+/g, " ")
                        .trim()
                        .toLowerCase();

                    const visible = (el) => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return rect.width > 0 && rect.height > 0 &&
                            style.display !== "none" && style.visibility !== "hidden";
                    };

                    const objetivo = normalizar(etiqueta);
                    const labels = [...document.querySelectorAll("label, span, div, td")]
                        .filter(visible)
                        .filter(el => normalizar(el.textContent).startsWith(objetivo));

                    const campos = [...document.querySelectorAll("input, textarea")]
                        .filter(visible)
                        .filter(el => !el.disabled && el.type !== "hidden");

                    for (const label of labels) {
                        const lr = label.getBoundingClientRect();
                        const candidatos = campos
                            .map(campo => ({ campo, rect: campo.getBoundingClientRect() }))
                            .filter(item => item.rect.left > lr.left)
                            .filter(item => Math.abs(item.rect.top - lr.top) < 40)
                            .sort((a, b) =>
                                Math.abs(a.rect.top - lr.top) - Math.abs(b.rect.top - lr.top) ||
                                a.rect.left - b.rect.left
                            );

                        if (candidatos.length) {
                            return candidatos[0].campo;
                        }
                    }

                    return null;
                }
                """,
                etiqueta,
            )

            elemento = handle.as_element()
            if elemento:
                return elemento

        raise RuntimeError(f"No se encontró el campo '{etiqueta}'")

    async def cerrar(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        self.log("Navegador cerrado.")
