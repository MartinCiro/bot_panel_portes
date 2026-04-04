# controller/Login.py
from asyncio import sleep as asy_slp
from os import path as os_path, makedirs
from random import uniform

class Login:
    """
    Login con Playwright - Single User.
    ✅ Page inyectada desde main, ✅ While 3 intentos, ✅ Sin browser init/close
    """
    
    # 🎯 XPaths
    XPATH_USERNAME_FIELD = "//input[@name='username']"
    XPATH_PASSWORD_FIELD = "//input[@name='password']"
    XPATH_LOGIN_BUTTON = "//button[contains(normalize-space(text()), 'Acceder')]"
    COOKIES_PATH = "./cookies/login_state.json"

    def __init__(self, config, user: str, password: str, page):
        """
        Args:
            config: Config instance
            user: Usuario
            password: Contraseña
            page: Playwright page (inyectada desde main)
        """
        self.config = config
        self.user = user
        self.password = password
        self.page = page  # ✅ Reusa página de main

    def _cookies_exist(self) -> bool:
        """Verifica si existe storage state guardado"""
        return os_path.exists(Login.COOKIES_PATH)

    async def _save_cookies(self):
        """Guarda el estado completo de la sesión"""
        try:
            if self.page and self.page.context:
                makedirs(os_path.dirname(Login.COOKIES_PATH), exist_ok=True)
                await self.page.context.storage_state(path=Login.COOKIES_PATH)
                self.config.log.comentario("SUCCESS", f"Cookies guardadas")
        except Exception as e:
            self.config.log.error(f"Error guardando cookies: {e}", "SAVE_COOKIES")

    async def _is_logged_in(self) -> bool:
        """
        Verifica si el usuario ya está logueado usando XPath.
        Returns:
            bool: True si encuentra el indicador de sesión activa
        """
        try:
            locator = self.page.locator(f'xpath={self.config.XPATH_LOGGED_INDICATOR}')
            return await locator.count() > 0
        except Exception as e:
            self.config.log.comentario("DEBUG", f"Error verificando login: {e}")
            return False

    async def _is_on_login_page(self) -> bool:
        """Verifica si estamos en página de login"""
        try:
            locator = self.page.locator(f'xpath={Login.XPATH_USERNAME_FIELD}')
            return await locator.count() > 0
        except:
            return False

    async def _perform_login_attempt(self) -> bool:
        """Ejecuta un intento de login"""
        try:
            self.config.log.proceso("Navegando a página de login")

            await self.page.goto(
                self.config.panel_login_url,
                wait_until="domcontentloaded",
                timeout=self.config.timeout * 1000
            )
            await self.page.wait_for_load_state("networkidle")
            await asy_slp(uniform(0.5, 1.5))

            if not await self._is_on_login_page():
                self.config.log.error("No se encontró el campo de usuario - ¿URL correcta?", "LOGIN_VALIDATION")
                return False

            self.config.log.proceso("Ingresando credenciales")

            # Llenar campos
            await self.page.locator(f'xpath={Login.XPATH_USERNAME_FIELD}').fill(
                self.user, 
                timeout=5000
            )
            await asy_slp(uniform(0.2, 0.5))

            await self.page.locator(f'xpath={Login.XPATH_PASSWORD_FIELD}').fill(
                self.password, 
                timeout=5000
            )
            await asy_slp(uniform(0.3, 0.8))

            # Click en Acceder
            self.config.log.proceso("Presionando botón de acceso")
            await self.page.locator(f'xpath={Login.XPATH_LOGIN_BUTTON}').click(
                timeout=5000, 
                delay=50
            )
            # return True
            # 5. Esperar navegación/respuesta
            await self.page.wait_for_load_state("networkidle")
            await asy_slp(uniform(1, 2))

            # 6. Verificar éxito
            if await self._is_logged_in():
                self.config.log.comentario("SUCCESS", "Login exitoso")
                await self._save_cookies()
                return True

            return False
        except Exception as e:
            self.config.log.error(f"Error en intento de login: {e}", "LOGIN_ATTEMPT")
            return False

    async def login(self, use_cookies: bool = True) -> bool:
        """
        Login principal con while de 3 intentos.
        """
        self.config.log.inicio_proceso(f"LOGIN - {self.user}")

        # 🔹 Intentar con cookies primero
        if use_cookies and self._cookies_exist():
            try:
                await self.page.goto(
                    self.config.panel_portabilidades_url,
                    wait_until="domcontentloaded",
                    timeout=self.config.timeout * 1000
                )
                await asy_slp(1)
                if await self._is_logged_in():
                    self.config.log.comentario("SUCCESS", "Sesión válida desde cookies")
                    self.config.log.fin_proceso(f"LOGIN - {self.user}")
                    return True
            except:
                pass
            self.config.log.comentario("INFO", "Cookies inválidas, procediendo con login")

        # 🔹 While loop: 3 intentos máximos
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            self.config.log.proceso(f"Intento {attempt}/{max_attempts}")
            
            if await self._perform_login_attempt():
                self.config.log.comentario("SUCCESS", "Login exitoso")
                self.config.log.fin_proceso(f"LOGIN - {self.user}")
                return True
            
            if attempt < max_attempts:
                delay = uniform(1.0, 2.5)
                self.config.log.comentario("INFO", f"Reintentando en {delay:.1f}s...")
                await asy_slp(delay)

        self.config.log.error("Se agotaron los intentos de login", "LOGIN_MAX_ATTEMPTS")
        self.config.log.fin_proceso(f"LOGIN - {self.user}")
        return False