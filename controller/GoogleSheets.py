# controller/GoogleSheets.py
from typing import List, Union
from os import path as os_path
from gspread import authorize, SpreadsheetNotFound, WorksheetNotFound
from google.oauth2.service_account import Credentials
from datetime import datetime

class GoogleSheets:
    """
    Integración con Google Sheets API para inserción de datos.
    ✅ Auth via service account, ✅ Logging con Config, ✅ Helpers opcional
    """
    
    # 🔐 Scopes necesarios para Sheets + Drive
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self, config, helpers=None):
        """
        Args:
            config: Instancia de Config (para logging y paths)
            helpers: Instancia de Helpers (opcional, para utilities)
        """
        self.config = config
        self.helpers = helpers
        
        # 🔧 Clientes de API (se inicializan en _connect())
        self._client = None
        self._spreadsheet = None
        self._worksheet = None
        
        # 📋 Configuración desde .env
        self.credentials_path = config._get_env_variable("GSHEET_CREDENTIALS_PATH")
        self.spreadsheet_name = config._get_env_variable("GSHEET_SPREADSHEET_NAME", None)
        self.spreadsheet_id = config._get_env_variable("GSHEET_SPREADSHEET_ID", None)
        self.worksheet_name = config._get_env_variable("GSHEET_WORKSHEET_NAME", "Hoja1")
        self.append_mode = config._get_env_variable("GSHEET_APPEND_MODE", "true").lower() == "true"
        self.include_timestamp = config._get_env_variable("GSHEET_INCLUDE_TIMESTAMP", "true").lower() == "true"

    def _connect(self) -> bool:
        """
        Establece conexión con Google Sheets API.
        Returns:
            bool: True si la conexión fue exitosa
        """
        try:
            if self._client:
                return True  # Ya conectado
            
            # Validar credenciales
            if not os_path.exists(self.credentials_path):
                self.config.log.error(
                    f"Archivo de credenciales no encontrado: {self.credentials_path}", 
                    "GSHEET_AUTH"
                )
                return False
            
            # Autenticar con service account
            creds = Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=self.SCOPES
            )
            self._client = authorize(creds)
            
            self.config.log.comentario("SUCCESS", "Conectado a Google Sheets API")
            return True
            
        except Exception as e:
            self.config.log.error(f"Error de autenticación: {e}", "GSHEET_AUTH")
            return False

    def open_spreadsheet(self, name: str = None, sheet_id: str = None) -> bool:
        """
        Abre una hoja de cálculo por nombre o ID.
        Args:
            name: Nombre del spreadsheet (opcional)
            sheet_id: ID del spreadsheet (opcional, más preciso)
        Returns:
            bool: True si se abrió exitosamente
        """
        if not self._connect():
            return False
        
        try:
            target_name = name or self.spreadsheet_name
            target_id = sheet_id or self.spreadsheet_id
            
            if target_id:
                self._spreadsheet = self._client.open_by_key(target_id)
                self.config.log.comentario("INFO", f"Spreadsheet abierto por ID: {target_id}")
            elif target_name:
                self._spreadsheet = self._client.open(target_name)
                self.config.log.comentario("INFO", f"Spreadsheet abierto por nombre: {target_name}")
            else:
                self.config.log.error("Debe especificar nombre o ID del spreadsheet", "GSHEET_OPEN")
                return False
            
            return True
            
        except SpreadsheetNotFound:
            self.config.log.error(
                f"Spreadsheet no encontrado: {target_name or target_id}", 
                "GSHEET_NOT_FOUND"
            )
            return False
        except Exception as e:
            self.config.log.error(f"Error abriendo spreadsheet: {e}", "GSHEET_OPEN")
            return False

    def select_worksheet(self, name: str = None, index: int = 0) -> bool:
        """
        Selecciona una hoja dentro del spreadsheet.
        Args:
            name: Nombre de la worksheet (opcional)
            index: Índice de la worksheet (0-based, si no se especifica nombre)
        Returns:
            bool: True si se seleccionó exitosamente
        """
        if not self._spreadsheet:
            self.config.log.error("No hay spreadsheet abierto", "GSHEET_WORKSHEET")
            return False
        
        try:
            target_name = name or self.worksheet_name
            
            # Intentar por nombre primero
            try:
                self._worksheet = self._spreadsheet.worksheet(target_name)
                self.config.log.comentario("INFO", f"Worksheet seleccionada: {target_name}")
                return True
            except WorksheetNotFound:
                # Si no existe y estamos en modo append, crearla
                if self.append_mode:
                    self._worksheet = self._spreadsheet.add_worksheet(
                        title=target_name, 
                        rows=1000, 
                        cols=20
                    )
                    self.config.log.comentario("SUCCESS", f"Worksheet creada: {target_name}")
                    return True
                else:
                    # Fallback a índice
                    worksheets = self._spreadsheet.worksheets()
                    if 0 <= index < len(worksheets):
                        self._worksheet = worksheets[index]
                        self.config.log.comentario("INFO", f"Worksheet por índice {index}: {self._worksheet.title}")
                        return True
                    
                    self.config.log.error(f"Worksheet no encontrada: {target_name}", "GSHEET_WORKSHEET")
                    return False
                    
        except Exception as e:
            self.config.log.error(f"Error seleccionando worksheet: {e}", "GSHEET_WORKSHEET")
            return False

    def append_row(self, data: Union[List, dict], add_timestamp: bool = None) -> bool:
        """
        Agrega una fila al final de la hoja.
        Args:
            data: Lista de valores o diccionario {header: value}
            add_timestamp: Si True, agrega columna con timestamp actual
        Returns:
            bool: True si se insertó exitosamente
        """
        if not self._worksheet:
            self.config.log.error("No hay worksheet seleccionada", "GSHEET_APPEND")
            return False
        
        try:
            # Convertir dict a lista si es necesario
            if isinstance(data, dict):
                # Si hay headers en la hoja, mapear por nombre de columna
                headers = self._worksheet.row_values(1)
                if headers:
                    row = [data.get(h, "") for h in headers]
                else:
                    row = list(data.values())
            else:
                row = list(data) if isinstance(data, (list, tuple)) else [data]
            
            # Agregar timestamp si está configurado
            if add_timestamp is None:
                add_timestamp = self.include_timestamp
                
            if add_timestamp:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if self.helpers:
                    timestamp = self.helpers.get_current_time()
                row.append(timestamp)
            
            # Insertar fila
            self._worksheet.append_row(row, value_input_option="USER_ENTERED")
            
            self.config.log.comentario(
                "SUCCESS", 
                f"Fila agregada: {len(row)} columnas" + (" + timestamp" if add_timestamp else "")
            )
            return True
            
        except Exception as e:
            self.config.log.error(f"Error agregando fila: {e}", "GSHEET_APPEND")
            return False

    def append_rows(self, rows: List[Union[List, dict]], add_timestamp: bool = None) -> dict:
        """
        Agrega múltiples filas en una sola operación (más eficiente).
        Args:
            rows: Lista de filas (cada una puede ser list o dict)
            add_timestamp: Si True, agrega columna con timestamp a cada fila
        Returns:
            dict: {"success": int, "failed": int, "error": str|None}
        """
        if not self._worksheet:
            return {"success": 0, "failed": 0, "error": "No worksheet selected"}
        
        try:
            success_count = 0
            failed_count = 0
            
            # Preparar todas las filas
            values_to_append = []
            for row in rows:
                if isinstance(row, dict):
                    headers = self._worksheet.row_values(1)
                    if headers:
                        row_data = [row.get(h, "") for h in headers]
                    else:
                        row_data = list(row.values())
                else:
                    row_data = list(row) if isinstance(row, (list, tuple)) else [row]
                
                if add_timestamp is None and self.include_timestamp:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if self.helpers:
                        timestamp = self.helpers.get_current_time()
                    row_data.append(timestamp)
                
                values_to_append.append(row_data)
            
            # Insertar en batch (más rápido que fila por fila)
            if values_to_append:
                self._worksheet.append_rows(
                    values_to_append, 
                    value_input_option="USER_ENTERED",
                    table_range=f"A1"  # Insertar desde la primera fila disponible
                )
                success_count = len(values_to_append)
                self.config.log.comentario("SUCCESS", f"{success_count} filas agregadas")
            
            return {"success": success_count, "failed": failed_count, "error": None}
            
        except Exception as e:
            self.config.log.error(f"Error agregando filas: {e}", "GSHEET_BATCH_APPEND")
            return {"success": 0, "failed": len(rows), "error": str(e)}

    def update_cell(self, row: int, col: int, value: str) -> bool:
        """
        Actualiza una celda específica.
        Args:
            row: Número de fila (1-based)
            col: Número de columna (1-based, A=1, B=2, etc.)
            value: Valor a insertar
        Returns:
            bool: True si se actualizó exitosamente
        """
        if not self._worksheet:
            return False
        
        try:
            self._worksheet.update_cell(row, col, value)
            self.config.log.comentario("SUCCESS", f"Celda [{row},{col}] actualizada")
            return True
        except Exception as e:
            self.config.log.error(f"Error actualizando celda: {e}", "GSHEET_UPDATE")
            return False

    def clear_worksheet(self, keep_headers: bool = True) -> bool:
        """
        Limpia el contenido de la worksheet.
        Args:
            keep_headers: Si True, preserva la primera fila (encabezados)
        Returns:
            bool: True si se limpió exitosamente
        """
        if not self._worksheet:
            return False
        
        try:
            if keep_headers:
                # Obtener headers y limpiar desde la fila 2
                headers = self._worksheet.row_values(1)
                if headers:
                    last_row = self._worksheet.row_count
                    if last_row > 1:
                        self._worksheet.clear(f"A2:Z{last_row}")
            else:
                self._worksheet.clear()
            
            self.config.log.comentario("SUCCESS", "Worksheet limpiada")
            return True
            
        except Exception as e:
            self.config.log.error(f"Error limpiando worksheet: {e}", "GSHEET_CLEAR")
            return False

    def get_headers(self) -> List[str]:
        """Retorna los encabezados de la primera fila"""
        if not self._worksheet:
            return []
        try:
            return self._worksheet.row_values(1)
        except:
            return []

    def set_headers(self, headers: List[str]) -> bool:
        """
        Establece los encabezados en la primera fila.
        Args:
            headers: Lista de nombres de columna
        Returns:
            bool: True si se establecieron exitosamente
        """
        if not self._worksheet:
            return False
        try:
            self._worksheet.update('A1', [headers], value_input_option="USER_ENTERED")
            self.config.log.comentario("SUCCESS", f"Encabezados establecidos: {headers}")
            return True
        except Exception as e:
            self.config.log.error(f"Error estableciendo headers: {e}", "GSHEET_HEADERS")
            return False

    def disconnect(self):
        """Cierra la conexión (opcional, gspread maneja el lifecycle)"""
        self._client = None
        self._spreadsheet = None
        self._worksheet = None
        self.config.log.comentario("INFO", "Conexión a Google Sheets cerrada")