# main.py
from asyncio import run as run_asy
from sys import exit
from playwright.async_api import async_playwright
from controller.Config import Config
from controller.Login import Login
from controller.Port import Port

async def init_browser(config: Config):
    """Inicializa Playwright y retorna (playwright, browser, context, page)"""
    from os import path as os_path  # ✅ Importar para verificar existencia
    
    playwright = await async_playwright().start()
    
    launch_options = {
        'headless': config.headless.lower() == 'true',
        'args': [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--window-size=1920,1080',
        ]
    }
    
    chrome_path = config.get_chrome_path()
    if chrome_path:
        launch_options['executable_path'] = chrome_path
    
    browser = await playwright.chromium.launch(**launch_options)
    
    # 🍪 Solo cargar storage_state si el archivo EXISTS
    cookies_path = config.get_cookies_path()
    storage_state = None
    if os_path.exists(cookies_path):  # ✅ Verificar antes de pasar
        storage_state = cookies_path
        config.log.comentario("INFO", f"Cargando cookies desde: {cookies_path}")
    else:
        config.log.comentario("INFO", "No hay cookies guardadas, inicio limpio")
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        storage_state=storage_state  # ✅ None si no existe el archivo
    )
    page = await context.new_page()
    
    return playwright, browser, page

async def run_full_flow(config: Config) -> int:
    """Orquesta: Login (3 intentos) → Port (sin reintentos)"""
    
    print(f"\n{'='*70}")
    print("🚀 LOGIN + EXTRACCIÓN PORTABILIDADES")
    print(f"{'='*70}\n")
    
    # 🔧 Inicializar navegador (main gestiona lifecycle)
    print("🌐 Inicializando navegador...")
    playwright, browser, page = await init_browser(config)
    
    try:
        # 🔐 Fase 1: Login con while(3 intentos)
        print("🔐 Fase 1: Login")
        login = Login(config, config.user_panel, config.ps_panel, page)
        
        if not await login.login():
            print("❌ Login fallido después de 3 intentos")
            return 1
        print("✅ Login exitoso\n")
        
        # 📊 Fase 2: Extracción (sin reintentos)
        print("📊 Fase 2: Extracción")
        port = Port(config, page)
        result = await port.extract_portabilidades()
        
        # 📋 Procesar resultado
        print(f"\n{'-'*70}")
        if result["status"] == "success":
            print("✅ EXTRACCIÓN EXITOSA")
            print(f"📦 Registros: {result.get('total_extracted', 0)}")
            return 0
        elif result["status"] == "no logged":
            print("⚠️  SESIÓN NO ACTIVA (sin reintentos)")
            print(f"💡 {result.get('error')}")
            return 2
        else:
            print("❌ EXTRACCIÓN FALLIDA")
            print(f"💥 {result.get('error')}")
            return 1
            
    finally:
        # 🧹 Cerrar navegador (siempre, al final)
        print(f"\n🔚 Cerrando navegador...")
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
        print("✅ Recursos liberados")

async def main():
    try:
        config = Config()
        print(f"⚙️ Modo: {'📁 LOCAL' if config.is_local_mode() else '🌐 REMOTO'}")
        print(f"👤 Usuario: {config.user_panel}")
        
        exit_code = await run_full_flow(config)
        
        print(f"\n{'='*70}")
        print("✅ PROCESO FINALIZADO" if exit_code == 0 else "❌ PROCESO FALLIDO")
        print(f"{'='*70}\n")
        return exit_code
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrumpido por usuario")
        return 130
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        import traceback; traceback.print_exc()
        return 1

def run():
    exit_code = run_asy(main())
    exit(exit_code)

if __name__ == "__main__":
    run()