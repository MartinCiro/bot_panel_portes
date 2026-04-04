# controller/Port.py
from asyncio import sleep as asy_slp
from random import uniform
from datetime import datetime

class Port:
    """
    Extracción de portabilidades con Playwright - Single User.
    ✅ XPath puro, ✅ Filtros dinámicos, ✅ JSON de salida
    """
    
    # 🎯 XPaths para navegación y validación
    XPATH_PORTADA_TITLE = "//h1[contains(normalize-space(text()), 'Portabilidades')]"
    XPATH_TIPO_PT_ARROW = "//label[contains(@class, 'select-label') and contains(text(), 'Tipo')]/following-sibling::span[@class='select-arrow']"
    XPATH_PT_ENTRA = "//span[contains(normalize-space(text()), 'Entrante')]"
    XPATH_ESTADO_PT_ARROW = "//select[@id='portability_search_status']/preceding-sibling::div/span[@class='select-arrow']"
    XPATH_ESTADO_PT = "//option[@value='APOR']"
    
    # 🎯 XPaths para tabla y validación de datos
    XPATH_TABLE_BODY = "//tbody[@class='datatable-body']"
    XPATH_TYPE_COLUMN = "//td[@data-mdb-field='type']"
    XPATH_PAGINATOR_SELECT = "//select[starts-with(@class, 'datatable-select')]"
    XPATH_PAGINATOR_200 = "//select[starts-with(@class, 'datatable-select')]/option[@value='200']"
    
    # 🎯 Columnas a extraer (índices base 1 para XPath)
    COLUMNS_TO_EXTRACT = {
        'fecha_solicitud': 1,      # td[1] - requestDate
        'documento_identidad': 3,  # td[3] - fiscalId  
        'operador_donante': 8      # td[8] - donorOpe
    }

    def __init__(self, config, page):  
        """
        Args:
            config: Instancia de Config
            page: Instancia de Playwright page (inyectada desde main)
        """
        self.config = config
        self.page = page 
        self.extracted_data = []

    async def _is_on_portabilidades_page(self) -> bool:
        """
        Verifica si estamos en la página de Portabilidades.
        Returns:
            str: "logged" si está en portabilidades, "no logged" si no, "error" si falla
        """
        try:
            locator = self.page.locator(f'xpath={Port.XPATH_PORTADA_TITLE}')
            count = await locator.count()
            return "logged" if count > 0 else "no logged"
        except Exception as e:
            self.config.log.comentario("DEBUG", f"Error verificando página: {e}")
            return "error"

    async def _apply_tipo_filter(self) -> bool:
        """Aplica filtro Tipo → Entrante"""
        try:
            self.config.log.proceso("Aplicando filtro: Tipo = Entrante")
            
            # Click en flecha del dropdown Tipo
            await self.page.locator(f'xpath={Port.XPATH_TIPO_PT_ARROW}').click(
                timeout=10000, delay=50
            )
            await asy_slp(uniform(0.3, 0.7))
            
            # Seleccionar "Entrante"
            await self.page.locator(f'xpath={Port.XPATH_PT_ENTRA}').click(
                timeout=10000, delay=50
            )
            await asy_slp(uniform(0.5, 1.2))  # Esperar actualización de tabla
            
            return True
        except Exception as e:
            self.config.log.error(f"Error aplicando filtro Tipo: {e}", "PORT_FILTER_TIPO")
            return False

    async def _apply_estado_filter(self) -> bool:
        """Aplica filtro Estado → APOR (Portada)"""
        try:
            self.config.log.proceso("Aplicando filtro: Estado = APOR")
            
            # Click en flecha del dropdown Estado
            await self.page.locator(f'xpath={Port.XPATH_ESTADO_PT_ARROW}').click(
                timeout=10000, delay=50
            )
            await asy_slp(uniform(0.3, 0.7))
            
            # Seleccionar "APOR"
            await self.page.locator(f'xpath={Port.XPATH_ESTADO_PT}').click(
                timeout=10000, delay=50
            )
            await asy_slp(uniform(0.8, 1.5))  # Esperar carga de resultados
            
            return True
        except Exception as e:
            self.config.log.error(f"Error aplicando filtro Estado: {e}", "PORT_FILTER_ESTADO")
            return False

    async def _verify_entrante_rows(self, rows_to_check: int = 3) -> bool:
        """
        Verifica que las primeras N filas tengan "Entrante" en la columna Tipo.
        XPath dinámico: (//tbody[@class='datatable-body']//td[@data-mdb-field='type' and contains(text(), 'Entrante')])[N]
        """
        try:
            self.config.log.proceso(f"Verificando {rows_to_check} filas con Tipo='Entrante'")
            
            for i in range(1, rows_to_check + 1):
                # XPath con índice dinámico (1-based)
                xpath = f"(//tbody[@class='datatable-body']//td[@data-mdb-field='type' and contains(text(), 'Entrante')])[{i}]"
                locator = self.page.locator(f'xpath={xpath}')
                
                count = await locator.count()
                if count == 0:
                    self.config.log.comentario("WARNING", f"Fila {i} no tiene 'Entrante' en columna Tipo")
                    return False
                    
            self.config.log.comentario("SUCCESS", f"Las {rows_to_check} primeras filas validadas como 'Entrante'")
            return True
            
        except Exception as e:
            self.config.log.error(f"Error verificando filas Entrante: {e}", "PORT_VERIFY")
            return False

    async def _apply_paginator_200(self) -> bool:
        """Aplica paginador para mostrar 200 registros por página"""
        try:
            self.config.log.proceso("Aplicando paginador: 200 registros")
            
            # Esperar que el select esté disponible
            paginator = self.page.locator(f'xpath={Port.XPATH_PAGINATOR_SELECT}')
            await paginator.wait_for(state='visible', timeout=10000)
            
            # Seleccionar opción "200"
            await self.page.locator(f'xpath={Port.XPATH_PAGINATOR_200}').click(
                timeout=10000, delay=50
            )
            await asy_slp(uniform(1.0, 2.0))  # Esperar recarga de tabla
            
            return True
        except Exception as e:
            self.config.log.comentario("WARNING", f"No se pudo aplicar paginador 200 (puede no ser necesario): {e}")
            # No es error fatal, continuar
            return True

    async def _extract_row_data(self, row_index: int) -> dict:
        """
        Extrae datos de una fila específica de la tabla.
        Args:
            row_index: Índice de fila (1-based para XPath)
        Returns:
            dict: Datos extraídos o None si falla
        """
        try:
            row_data = {}
            
            for field_name, col_index in Port.COLUMNS_TO_EXTRACT.items():
                # XPath: //tbody[@class='datatable-body']/tr[N]/td[M]
                xpath = f"//tbody[@class='datatable-body']/tr[{row_index}]/td[{col_index}]"
                locator = self.page.locator(f'xpath={xpath}')
                
                # Obtener texto limpio (sin HTML anidado)
                text = await locator.text_content()
                if text:
                    row_data[field_name] = text.strip()
                else:
                    # Fallback: intentar obtener desde atributo o elemento hijo
                    row_data[field_name] = await locator.evaluate('el => el.textContent?.trim() || ""')
            
            # Agregar metadatos
            row_data['row_index'] = row_index
            row_data['extracted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return row_data
            
        except Exception as e:
            self.config.log.comentario("WARNING", f"Error extrayendo fila {row_index}: {e}")
            return None

    async def _extract_table_data(self, max_rows: int = None) -> list:
        """
        Extrae datos de la tabla completa.
        Args:
            max_rows: Límite de filas a extraer (None = todas)
        Returns:
            list: Lista de diccionarios con datos extraídos
        """
        try:
            self.config.log.proceso("Extrayendo datos de la tabla")
            
            # Contar filas disponibles
            rows_locator = self.page.locator(f'{Port.XPATH_TABLE_BODY}/tr')
            total_rows = await rows_locator.count()
            
            if total_rows == 0:
                self.config.log.comentario("INFO", "Tabla vacía o sin resultados")
                return []
            
            # Determinar cuántas filas procesar
            rows_to_process = min(max_rows, total_rows) if max_rows else total_rows
            self.config.log.comentario("INFO", f"Procesando {rows_to_process} de {total_rows} filas")
            
            extracted = []
            for i in range(1, rows_to_process + 1):  # XPath es 1-based
                row_data = await self._extract_row_data(i)
                if row_data:
                    extracted.append(row_data)
                    # Pequeño delay para no saturar
                    if i % 10 == 0:
                        await asy_slp(0.1)
            
            self.config.log.comentario("SUCCESS", f"Datos extraídos: {len(extracted)} registros")
            return extracted
            
        except Exception as e:
            self.config.log.error(f"Error extrayendo tabla: {e}", "PORT_EXTRACT")
            return []

    async def extract_portabilidades(self, max_rows: int = None) -> dict:
        """Flujo principal de extracción"""
        result = {"status": "error", "data": [], "error": None}
        
        try:
            self.config.log.inicio_proceso("EXTRACCIÓN PORTABILIDADES")
            
            # Navegar a portabilidades
            await self.page.goto(
                self.config.panel_portabilidades_url,
                wait_until="domcontentloaded",
                timeout=self.config.timeout * 1000
            )
            await self.page.wait_for_load_state("networkidle")
            await asy_slp(uniform(0.5, 1.5))
            
            # Verificar login
            login_status = await self._is_on_portabilidades_page()
            
            if login_status == "no logged":
                result["status"] = "no logged"
                result["error"] = "Session not active"
                return result  # 🚫 Sin reintentos
            
            if login_status == "error":
                result["error"] = "Error verificando sesión"
                return result
            
            # Aplicar filtros
            if not await self._apply_tipo_filter():
                result["error"] = "Falló filtro Tipo"
                return result
            if not await self._apply_estado_filter():
                result["error"] = "Falló filtro Estado"
                return result
            
            # Validar filas (warning si falla)
            await self._verify_entrante_rows(3)
            
            # Paginador
            await self._apply_paginator_200()
            
            # Extraer e imprimir
            extracted = await self._extract_table_data(max_rows=max_rows)
            if extracted:
                print(f"\n📊 Datos extraídos ({len(extracted)}):")
                for row in extracted:
                    print(f"   • {row}")
            
            result["status"] = "success"
            result["data"] = extracted
            result["total_extracted"] = len(extracted)
            return result
            
        except Exception as e:
            self.config.log.error(f"Error crítico: {e}", "PORT_FLOW")
            result["error"] = str(e)
            return result

    def get_extracted_data(self) -> list:
        """Retorna los datos extraídos (útil para uso en memoria)"""
        return self.extracted_data