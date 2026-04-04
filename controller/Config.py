# controller/Config.py
from typing import Optional
from re import match

from dotenv import load_dotenv
from os import path as os_path, makedirs, getenv
from controller.Log import Log

class Config:
    """
    Clase de configuración global para Panel.
    ✅ Soporta file:// y http/https
    ✅ Normaliza protocolo con regex si falta
    ✅ Cambio de entorno solo editando .env
    """

    def __init__(self) -> None:
        """Constructor"""
        load_dotenv()
        self.log = Log()
        
        # 🔑 CREDENCIALES DEL ÚNICO USUARIO
        self.user_panel: str = self._get_env_variable("USER_PANEL")
        self.ps_panel: str = self._get_env_variable("PASS_PANEL")
        self.headless: str = self._get_env_variable("HEADLESS", "true")
        
        # 🌐 URLs PANELDIGITAL (se normalizan con protocolo si es necesario)
        raw_base = self._get_env_variable("PANEL_BASE_URL")
        self.panel_base_url: str = self._normalize_url(raw_base)
        
        # URLs derivadas: si no están en .env, se construyen desde base_url
        self.panel_login_url: str = self._normalize_url(
            self._get_env_variable(
                "PANEL_LOGIN_URL", 
                f"{self.panel_base_url}/login/Log%20in%20-%20Panel.html"
            )
        )
        self.panel_portabilidades_url: str = self._normalize_url(
            self._get_env_variable(
                "PANEL_PORTABILIDADES_URL", 
                f"{self.panel_base_url}/logge/Portabilidades.html"
            )
        )

        # 🖥️ Ruta de Chrome (opcional)
        self.chrome_path: str = self._get_env_variable("CHROME_PATH", "")
        
        # 📁 RUTAS DE ALMACENAMIENTO
        self.cookies_base_path: str = "./cookies"
        self.logs_path: str = self._get_env_variable("LOGS_PATH", "./logs")
        
        # 🔄 CONFIGURACIÓN DE REINTENTOS Y TIMEOUTS
        self.max_retries: int = int(self._get_env_variable("MAX_RETRIES", "3"))
        self.retry_delay: float = float(self._get_env_variable("RETRY_DELAY", "5.0"))
        self.timeout: int = int(self._get_env_variable("TIMEOUT", "30"))
        
        # 📡 TELEGRAM (opcional)
        self.telegram_token: str = self._get_env_variable("TELEGRAM_TOKEN", "")
        self.telegram_chat: str = self._get_env_variable("TELEGRAM_CHAT", "")
        
        # ✅ Validar configuración al iniciar
        self.validate_config()
        
        # 📁 Crear directorios base si no existen
        self._init_directories()

        # Path compartidos
        self.XPATH_LOGGED_INDICATOR = "//span[@class='circle-user']"

    def _normalize_url(self, url: str) -> str:
        """
        Normaliza una URL asegurando que tenga protocolo.
        
        Comportamiento:
        - ✅ Si ya tiene http://, https://, file://, ftp:// → retorna sin cambios
        - ✅ Si NO tiene protocolo → agrega http:// por defecto
        - ✅ Limpia espacios y normaliza formato
        
        Regex explicada:
        ^[a-zA-Z][a-zA-Z0-9+.-]*://
        │   │              │    │
        │   │              │    └─ Literal "://"
        │   │              └─ Caracteres válidos en esquema (+, ., -, alfanum)
        │   └─ Primera letra del esquema (debe ser alfabética)
        └─ Inicio de la cadena
        
        Args:
            url: URL a normalizar (con o sin protocolo)
        Returns:
            str: URL con protocolo garantizado
        """
        if not url or not isinstance(url, str):
            return url or ""
        
        url = url.strip()
        
        # 🔍 Regex para detectar cualquier protocolo válido
        if match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
            return url  # Ya tiene protocolo, retornar tal cual
        
        # ➕ Agregar http:// por defecto si no tiene protocolo
        return f"http://{url}"

    def _sanitize_path(self, path_url: str) -> str:
        """
        Convierte una URL file:// a ruta de sistema para validaciones.
        Solo para uso interno en validaciones de archivos.
        """
        if path_url.lower().startswith("file://"):
            return path_url[7:]  
        return path_url

    def get_chrome_paths(self) -> list:
        """
        Retorna lista de paths posibles para Chrome/Chromium.
        Prioriza: 1) CHROME_PATH de .env → 2) Fallbacks por SO
        """
        import platform
        paths = []
        
        # 1️⃣ Si se especificó en .env y existe, usar ese primero
        if self.chrome_path and os_path.exists(os_path.expandvars(self.chrome_path)):
            paths.append(os_path.expandvars(self.chrome_path))
        
        # 2️⃣ Fallbacks por sistema operativo
        if platform.system().startswith("win"):
            paths.extend([
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
            ])
        elif platform.system().startswith("darwin"):
            paths.extend([
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ])
        else:  # Linux
            paths.extend([
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
            ])
        
        # 3️⃣ Filtrar solo los que existen realmente
        return [p for p in paths if os_path.exists(os_path.expandvars(p))]
    
    def get_chrome_path(self) -> Optional[str]:
        """Retorna el primer path válido de Chrome o None"""
        paths = self.get_chrome_paths()
        return paths[0] if paths else None

    def _get_env_variable(self, key: str, default: str = None) -> str:
        """Obtiene variable de entorno de forma segura"""
        value = getenv(key, default)
        if value is None and default is None:
            raise ValueError(f"⚠️ Variable de entorno requerida no encontrada: {key}")
        return value.strip() if value else value

    def _init_directories(self):
        """Crea directorios base si no existen"""
        for path_dir in [self.logs_path, self.cookies_base_path]:
            if not os_path.exists(path_dir):
                makedirs(path_dir, exist_ok=True)
                self.log.comentario("INFO", f"Directorio creado: {path_dir}")

    def get_cookies_path(self) -> str:
        """
        Retorna la ruta única del archivo de cookies/storage state.
        Compatible con Login.COOKIES_PATH
        """
        return os_path.join(self.cookies_base_path, "login_state.json")

    def clear_cookies(self):
        """Elimina el archivo de cookies para forzar un nuevo login"""
        cookies_path = self.get_cookies_path()
        if os_path.exists(cookies_path):
            try:
                from os import remove
                remove(cookies_path)
                self.log.comentario("INFO", "Cookies eliminadas - nuevo login requerido")
                return True
            except Exception as e:
                self.log.error(f"No se pudo eliminar cookies: {e}", "CLEAR_COOKIES")
                return False
        return False

    def validate_config(self):
        """Valida que la configuración mínima esté presente"""
        errors = []
        
        # Credenciales obligatorias
        if not self.user_panel:
            errors.append("USER_PANEL no configurado en .env")
        if not self.ps_panel:
            errors.append("PASS_PANEL no configurado en .env")
        
        # URLs críticas - validar que tengan protocolo válido
        valid_protocols = ('http://', 'https://', 'file://', 'ftp://')
        base_lower = self.panel_base_url.lower()
        
        if not any(base_lower.startswith(p) for p in valid_protocols):
            errors.append(f"panel_base_url debe tener protocolo válido. Actual: '{self.panel_base_url}'")
        
        # Si es file://, validar que el archivo/base exista (solo warning, no error fatal)
        if base_lower.startswith("file://"):
            local_path = self._sanitize_path(self.panel_base_url)
            if not os_path.exists(local_path):
                self.log.comentario(
                    "WARNING", 
                    f"Ruta local no encontrada (pero se permite): {local_path}"
                )
            
        if errors:
            for err in errors:
                self.log.error(err, "CONFIG_VALIDATION")
            raise ValueError("❌ Configuración inválida:\n" + "\n".join(errors))
        
        self.log.comentario("SUCCESS", "Configuración validada correctamente")
        return True

    def is_local_mode(self) -> bool:
        """
        Detecta si estamos en modo local (file://) o remoto (http/https).
        Útil para ajustar comportamientos según el entorno.
        Returns:
            bool: True si es archivo local, False si es URL remota
        """
        return self.panel_base_url.lower().startswith("file://")

    def get_env_summary(self) -> dict:
        """
        Retorna resumen de configuración para debug/logging.
        """
        return {
            "user": self.user_panel,
            "base_url": self.panel_base_url,
            "mode": "LOCAL" if self.is_local_mode() else "REMOTE",
            "headless": self.headless,
            "chrome_path": self.get_chrome_path() or "→ Chromium interno",
            "timeout": self.timeout,
        }

    def __repr__(self) -> str:
        """Representación legible para debug"""
        mode = "LOCAL" if self.is_local_mode() else "REMOTE"
        return (f"<Config user={self.user_panel!r}, "
                f"base_url={self.panel_base_url!r}, "
                f"mode={mode}, "
                f"timeout={self.timeout}s>")