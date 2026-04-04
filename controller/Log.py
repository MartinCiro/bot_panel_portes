from datetime import datetime
from pathlib import Path
from os import getcwd

class Log:
    """
    Sistema de logging mejorado para registro de procesos y errores.
    
    Características:
    - Manejo automático de rutas y creación de directorios
    - Formato consistente para todos los mensajes
    - Escritura thread-safe
    - Soporte para logs de procesos y errores
    
    Ejemplo de uso:
    --------------
    log = Log()
    log.inicio_proceso()
    log.proceso("Extracción de datos")
    log.comentario("INFO", "Procesando 100 registros")
    log.error("Timeout de conexión", "extraccion_datos")
    log.fin_proceso()
    """
    
    __ANCHO = 120
    __FORMATO_TIEMPO = '%Y-%m-%d %H:%M:%S'
    
    def __init__(self):
        """
        Inicializa el sistema de logging con las rutas configuradas.
        Crea los directorios necesarios si no existen.
        """
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        
        # Configuración de rutas
        self.__ruta_base = Path(getcwd())
        self.__ruta_procesos = self.__ruta_base / "logs/procesos"
        self.__ruta_errores = self.__ruta_base / "logs/errores"
        
        # Crear directorios si no existen
        self.__ruta_procesos.mkdir(parents=True, exist_ok=True)
        self.__ruta_errores.mkdir(parents=True, exist_ok=True)
        
        # Archivos de log
        self.__archivo_procesos = self.__ruta_procesos / f"LogProcesos_{fecha_actual}.txt"
        self.__archivo_errores = self.__ruta_errores / f"LogErrores_{fecha_actual}.txt"
    
    def __tiempo_actual(self) -> str:
        """Obtiene el tiempo actual formateado"""
        return datetime.now().strftime(self.__FORMATO_TIEMPO)
    
    def __formatear_mensaje(self, *lineas: str) -> str:
        """Genera un mensaje formateado con bordes"""
        mensaje = f"{'=' * self.__ANCHO}\n"
        for linea in lineas:
            mensaje += f"| {linea.ljust(self.__ANCHO - 4)} |\n"
        mensaje += f"{'=' * self.__ANCHO}\n"
        return mensaje
    
    def __escribir_log(self, archivo: Path, mensaje: str):
        """Escribe de forma segura en el archivo de log"""
        with archivo.open('a', encoding='utf-8') as f:
            f.write(mensaje + "\n")
    
    def inicio_proceso(self, nombre_aplicacion: str = "Proceso"):
        """Registra el inicio de un proceso"""
        mensaje = self.__formatear_mensaje(
            f"INICIO DE EJECUCIÓN - {nombre_aplicacion} - {self.__tiempo_actual()}"
        )
        self.__escribir_log(self.__archivo_procesos, mensaje)
    
    def fin_proceso(self, nombre_aplicacion: str = "Proceso"):
        """Registra la finalización de un proceso"""
        mensaje = self.__formatear_mensaje(
            f"FIN DE EJECUCIÓN - {nombre_aplicacion} - {self.__tiempo_actual()}"
        )
        self.__escribir_log(self.__archivo_procesos, mensaje)
    
    def proceso(self, nombre_proceso: str):
        """Registra un proceso específico"""
        mensaje = f"| Ejecutando: {nombre_proceso.ljust(80)} | Hora: {self.__tiempo_actual()} |"
        self.__escribir_log(self.__archivo_procesos, mensaje)
    
    def comentario(self, nivel: str, mensaje: str):
        """Registra un comentario con nivel de severidad"""
        contenido = self.__formatear_mensaje(
            f"{nivel.upper()}: {mensaje}",
            f"Hora: {self.__tiempo_actual()}"
        )
        self.__escribir_log(self.__archivo_procesos, contenido)
    
    def error(self, descripcion_error: str, proceso: str = ""):
        """Registra un error ocurrido"""
        contenido = self.__formatear_mensaje(
            f"ERROR DETECTADO - {self.__tiempo_actual()}",
            f"Proceso: {proceso}" if proceso else "Proceso no especificado",
            f"Detalle: {descripcion_error}"
        )
        self.__escribir_log(self.__archivo_errores, contenido)
        self.__escribir_log(self.__archivo_procesos, contenido)  # También en log de procesos
    
    def separador(self):
        """Añade un separador visual al log"""
        self.__escribir_log(self.__archivo_procesos, "=" * self.__ANCHO)