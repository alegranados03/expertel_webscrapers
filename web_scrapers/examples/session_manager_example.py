import os

from web_scrapers.application.session_manager import SessionManager
from web_scrapers.domain.entities.session import Carrier, Credentials
from web_scrapers.domain.enums import Navigators


def main():
    session_manager: SessionManager = SessionManager()

    # obtener nuevo mensaje (con rabbitMQ?)
    # obtener información de la BD, credenciales, billing cycle, account, billing cycle files (o usage), credenciales
    # si el request es de PDF deberá manejarse de otro modo
    credentials = Credentials(username="tu_usuario", password="tu_contraseña", carrier_type=Carrier.BELL)

    try:
        login_success = session_manager.login(credentials)
        if login_success:
            browser_wrapper = session_manager.get_browser_wrapper()
            if browser_wrapper:
                import time

                time.sleep(5)

            print(f"¿Sesión activa? {session_manager.refresh_session_status()}")
            session_manager.logout()
        else:
            print("✗ Error en login")
            if session_manager.has_error():
                print(f"Error: {session_manager.get_error_message()}")

    except Exception as e:
        print(f"Error durante la ejecución: {str(e)}")


def demo_environment_configuration():
    """Demuestra cómo usar configuración desde variables de entorno."""

    print("=== Demo de Configuración desde .env ===")

    # Mostrar configuración actual
    print("Configuración actual:")
    print(f"BROWSER_TYPE: {os.getenv('BROWSER_TYPE', 'chrome')}")
    print(f"BROWSER_HEADLESS: {os.getenv('BROWSER_HEADLESS', 'false')}")
    print(f"BROWSER_SLOW_MO: {os.getenv('BROWSER_SLOW_MO', '1000')}")
    print(f"BROWSER_TIMEOUT: {os.getenv('BROWSER_TIMEOUT', '30000')}")
    print(f"BROWSER_VIEWPORT_WIDTH: {os.getenv('BROWSER_VIEWPORT_WIDTH', '1920')}")
    print(f"BROWSER_VIEWPORT_HEIGHT: {os.getenv('BROWSER_VIEWPORT_HEIGHT', '1080')}")

    # Crear SessionManager sin especificar navegador (usará .env)
    with SessionManager() as session_manager:
        print(f"\nUsando navegador desde .env...")
        print(f"Navegadores disponibles: {session_manager.get_available_browsers()}")


if __name__ == "__main__":
    main()
