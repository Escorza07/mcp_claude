import os
import json
import re
import asyncio
import subprocess
from typing import Dict
from ...core.base_mcp import BaseMCP

class GmailMCP(BaseMCP):
    """Implementación específica para el MCP de Gmail."""
    
    def __init__(self):
        super().__init__("gmail")
        
    async def setup(self, path: str, env_vars: Dict) -> bool:
        """Configura el MCP de Gmail."""
        try:
            # 1. Verificar credenciales mínimas
            min_required = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REFRESH_TOKEN', 'GOOGLE_REDIRECT_URI']
            missing = [v for v in min_required if v not in env_vars]
            empty   = [v for v in min_required if v in env_vars and not env_vars[v].strip()]
            
            if missing:
                print(f"Faltan variables de entorno: {', '.join(missing)}")
                print("Configura las credenciales en repositories.json y vuelve a ejecutar.")
                return False
            if empty:
                print(f"Variables vacías: {', '.join(empty)}")
                print("Configura las credenciales en repositories.json y vuelve a ejecutar.")
                return False
            
            # 2. Crear archivo .env con las credenciales
            print("\nCreando archivo .env con credenciales...")
            self.create_env_file(path, env_vars)
            print(f"Archivo .env creado en: {os.path.join(path, '.env')}")

            # 3. Instalar dependencias
            print("\nInstalando dependencias...")
            await self.run_command(f"cd {path} && npm install")

            # 4. Construir el proyecto
            print("\nConstruyendo el proyecto...")
            await self.run_command(f"cd {path} && npm run build")

            # 5. Verificar que el servidor funciona
            print("\nVerificando que el servidor funciona...")
            if not await self.verify_server(path):
                print("Error: El servidor no pudo iniciar correctamente")
                return False
            
            return True
                
        except Exception as e:
            print(f"Error configurando Gmail: {e}")
            return False
            
    def get_config(self) -> Dict:
        """Obtiene la configuración específica de Gmail para Claude Desktop."""
        return {
            "command": "node",
            "args": ["dist/index.js"],
            "env": {
                "GOOGLE_CLIENT_ID": "",
                "GOOGLE_CLIENT_SECRET": "",
                "GOOGLE_REFRESH_TOKEN": "",
                "GOOGLE_REDIRECT_URI": ""
            }
        }

    def create_env_file(self, path: str, env_vars: Dict) -> None:
        """Crea el archivo .env con las variables de entorno."""
        env_path = os.path.join(path, '.env')
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                f.write(f'{key}="{value}"\n')

    async def verify_server(self, path: str) -> bool:
        """Verifica que el servidor funciona correctamente."""
        try:
            print("\nIntentando iniciar el servidor...")
            
            # Iniciar el servidor
            process = subprocess.Popen(
                "npm start",
                cwd=path,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Esperar un momento para ver si el servidor inicia
            await asyncio.sleep(2)
            
            # Verificar si el proceso sigue corriendo
            if process.poll() is None:
                print("Servidor iniciado correctamente!")
                print("Consejo: Para ver la salida completa del servidor, ejecuta 'npm start' en el CMD")
                
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