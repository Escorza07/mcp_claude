"""
Implementación del MCP de WhatsApp con manejo de instalación y configuración.
"""
import os
import subprocess
import sys
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from ...core.base_mcp import BaseMCP

class WhatsAppMCP(BaseMCP):
    """MCP para interactuar con WhatsApp."""

    def __init__(self):
        """Inicializa el MCP de WhatsApp."""
        super().__init__("whatsapp")
        self._client = None
        self._server_process: Optional[subprocess.Popen] = None
        self._bridge_process: Optional[subprocess.Popen] = None
        self._load_properties()

    def _load_properties(self):
        """Carga las propiedades desde default.properties"""
        try:
            # Obtener la ruta al directorio config
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            properties_path = os.path.join(project_root, 'config', 'default.properties')
            
            self.properties = {}
            if os.path.exists(properties_path):
                with open(properties_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            try:
                                key, value = line.split('=', 1)
                                self.properties[key.strip()] = value.strip()
                            except ValueError:
                                continue
        except Exception as e:
            print(f"Error cargando propiedades: {e}")
            self.properties = {}

    def _get_uv_path(self) -> str:
        """Obtiene la ruta de uv.exe desde las propiedades"""
        return self.properties.get('UV_PATH', '')

    def get_config(self) -> Dict[str, Any]:
        """Obtiene la configuración específica de WhatsApp para Claude Desktop.

        Returns:
            Dict[str, Any]: Configuración del MCP de WhatsApp.
        """
        uv_path = self._get_uv_path()
        if not uv_path or not os.path.exists(uv_path):
            print("Error: No se encontró la ruta de uv.exe en default.properties o el archivo no existe")
            print("Recordar que las rutas se establecen en default.properties luego de instalar: ")   
            print("manualmente el archivo tdm64-gcc y luego ejecutar install_dependencies en powershell para que se establezcan las rutas")  
            return {}

        # Obtener la ruta base de los repositorios y limpiarla
        base_path = self.properties.get('REPOSITORIES_BASE_PATH', '')
        if not base_path:
            print("Error: No se encontró REPOSITORIES_BASE_PATH en default.properties")
            return {}

        # Limpiar la ruta base de barras dobles
        base_path = base_path.replace("\\", "/").replace("//", "/")

        # Construir la ruta del servidor usando barras normales
        server_path = f"{base_path}/whatsapp-mcp/whatsapp-mcp-server"

        # Asegurar que las rutas usen barras normales y no tengan barras dobles
        uv_path = uv_path.replace("\\", "/").replace("//", "/")
        server_path = server_path.replace("//", "/")

        return {
            "command": uv_path,
            "args": [
                "--directory",
                server_path,
                "run",
                "main.py"
            ]
        }

    async def setup(self, path: str, env_vars: Dict[str, str]) -> bool:
        """Configura el entorno de WhatsApp MCP.

        Args:
            path: Ruta al directorio del MCP.
            env_vars: Variables de entorno para el MCP.

        Returns:
            bool: True si la configuración fue exitosa, False en caso contrario.
        """
        try:
            print("\nConfigurando WhatsApp MCP...")
            


            # 2. Verificar ruta de uv.exe
            uv_path = self._get_uv_path()
            if not uv_path or not os.path.exists(uv_path):
                print("Error: No se encontró la ruta de uv.exe en default.properties o el archivo no existe")
                return False

            # 1. Configurar el servidor
            server_path = Path(path) / "whatsapp-mcp-server"
            print(f"\nConfigurando servidor en: {server_path}")
            
            # 2. Crear entorno virtual
            print("Creando entorno virtual...")
            venv_path = server_path / ".venv"
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            print("Entorno virtual creado exitosamente")

            # 3. Activar entorno virtual y ejecutar comandos
            if sys.platform == "win32":
                activate_script = venv_path / "Scripts" / "activate.bat"
                pip_cmd = [str(venv_path / "Scripts" / "python.exe"), "-m", "pip"]
            else:
                activate_script = venv_path / "bin" / "activate"
                pip_cmd = [str(venv_path / "bin" / "python"), "-m", "pip"]

            # 4. Instalar dependencias
            print("\nInstalando dependencias...")
            subprocess.run(
                pip_cmd + ["install", "httpx>=0.28.1", "mcp[cli]>=1.6.0", "requests>=2.32.3"],
                check=True
            )
            print("Dependencias instaladas exitosamente")

            # 7. Mostrar instrucciones de inicio de sesión
            print("\n⚠️ IMPORTANTE: Para que WhatsApp funcione correctamente, necesitas configurar el servicio del bridge.")
            print("1. Debes ubicarte en la ruta donde tienes tu servidor de whatsapp'...whatsapp-mcp\whatsapp-bridge'")
            print("   Debes abrir una terminal en esa ruta y ejecuar el comando 'go run main.go'")
            print("   Al ejecutar el comando, te saldra un QR en tu terminal, debes escanearlo con tu whatsapp para iniciar sesion")
            print("   Luego de escanearlo, deberas esperar unos minutos para que se sincronice el whatsapp")
            print("   Al finalizar la sincronizacion puedes cerrar la ventana de tu terminal")
            print("2. Ejecuta el script 'setup_whatsapp_service.ps1' como administrador")
            print("   Este script instalará y configurará el servicio de WhatsApp Bridge")
            print("   Nota: El script requiere permisos de administrador")
            print("\n3. Si necesitas reiniciar el servicio:")
            print("   - Abre PowerShell como administrador")
            print("   - Ejecuta: Restart-Service whatsapp-bridge")
            print("\n4. Si por alguna razón deseas detener el servicio:")
            print("   - Abre PowerShell como administrador")
            print("   - Ejecuta: Stop-Service whatsapp-bridge")
            print("\n5. Si por alguna razón deseas eliminar el servicio:")
            print("   - Abre un CMD como administrador")
            print("   - Ejecuta: nssm remove whatsapp-bridge confirm")
            print("   - Luego ejecuta: taskkill /F /IM python.exe")
            print("   - Cierra el CMD")

            # 8. Verificar que el servidor funciona
            print("\nVerificando que el servidor funciona...")
            if not await self.verify_server(server_path):
                print("Error: El servidor no pudo iniciar correctamente")
                return False

            return True

        except Exception as e:
            print(f"Error al configurar WhatsApp MCP: {str(e)}")
            return False

    def _is_installed(self, path: str) -> bool:
        """Verifica si WhatsApp MCP ya está instalado.

        Args:
            path: Ruta al directorio del MCP.

        Returns:
            bool: True si está instalado, False en caso contrario.
        """
        try:
            # Verificar si los directorios necesarios existen
            server_path = Path(path) / "whatsapp-mcp-server"
            bridge_path = Path(path) / "whatsapp-bridge"
            
            if not server_path.exists() or not bridge_path.exists():
                print("Directorios del MCP no encontrados")
                return False
                
            # Verificar si el entorno virtual existe
            venv_path = server_path / ".venv"
            if not venv_path.exists():
                print("Entorno virtual no encontrado")
                return False
                
            # Verificar si las dependencias están instaladas
            if sys.platform == "win32":
                pip_path = venv_path / "Scripts" / "pip.exe"
            else:
                pip_path = venv_path / "bin" / "pip"
                
            if not pip_path.exists():
                print("Pip no encontrado en el entorno virtual")
                return False
                
            # Verificar si el servidor funciona
            try:
                # Intentar iniciar el servidor brevemente para verificar
                uv_path = Path.home() / ".uv" / "bin" / "uv.exe"
                if not uv_path.exists():
                    print("No se encontró el ejecutable uv")
                    return False
                    
                process = subprocess.Popen(
                    [str(uv_path), "--directory", str(server_path), "run", "main.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Esperar un momento para ver si el servidor inicia
                import time
                time.sleep(2)
                
                if process.poll() is not None:
                    print("El servidor no pudo iniciar correctamente")
                    return False
                    
                # Terminar el proceso de prueba
                process.terminate()
                time.sleep(1)
                if process.poll() is None:
                    process.kill()
                    
            except Exception as e:
                print(f"Error al verificar el servidor: {str(e)}")
                return False
                
            print("WhatsApp MCP está correctamente instalado y configurado")
            return True
            
        except Exception as e:
            print(f"Error al verificar la instalación: {str(e)}")
            return False

    async def verify_server(self, path: Path) -> bool:
        """Verifica que el servidor funciona correctamente.

        Args:
            path: Ruta al directorio del servidor.

        Returns:
            bool: True si el servidor funciona correctamente, False en caso contrario.
        """
        try:
            print("\nIntentando iniciar el servidor...")
            
            uv_path = self._get_uv_path()
            if not uv_path or not os.path.exists(uv_path):
                print("Error: No se encontró la ruta de uv.exe en default.properties o el archivo no existe")
                return False

            # Iniciar el servidor
            process = subprocess.Popen(
                [uv_path, "--directory", str(path), "run", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Esperar un momento para ver si el servidor inicia
            await asyncio.sleep(2)
            
            # Verificar si el proceso sigue corriendo
            if process.poll() is None:
                print("Servidor iniciado correctamente!")
                print("Consejo: Para ver la salida completa del servidor, ejecuta 'uv run main.py' en el CMD")
                
                # Intentar terminar el proceso de manera segura
                try:
                    process.terminate()
                    await asyncio.sleep(1)
                    if process.poll() is None:
                        process.kill()
                    await asyncio.sleep(1)
                except Exception:
                    pass
                    
                return True
            else:
                # Si el proceso terminó, leer la salida de error
                _, stderr = process.communicate()
                print("Error: El servidor no pudo iniciar correctamente")
                if stderr:
                    print("\nErrores encontrados:")
                    print(stderr.strip())
                return False
            
        except Exception as e:
            print(f"Error al verificar el servidor: {str(e)}")
            return False

    async def start(self) -> bool:
        """Inicia el servidor de WhatsApp MCP.

        Returns:
            bool: True si el servidor se inició correctamente, False en caso contrario.
        """
        try:
            uv_path = self._get_uv_path()
            if not uv_path or not os.path.exists(uv_path):
                print("Error: No se encontró la ruta de uv.exe en default.properties o el archivo no existe")
                return False

            # Iniciar el servidor
            server_path = Path("whatsapp-mcp") / "whatsapp-mcp-server"
            self._server_process = subprocess.Popen(
                [uv_path, "--directory", str(server_path), "run", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            return True

        except Exception as e:
            print(f"Error al iniciar el servidor: {str(e)}")
            return False

    async def stop(self) -> None:
        """Detiene el servidor de WhatsApp MCP."""
        if self._server_process:
            self._server_process.terminate()
            self._server_process = None

        if self._bridge_process:
            self._bridge_process.terminate()
            self._bridge_process = None