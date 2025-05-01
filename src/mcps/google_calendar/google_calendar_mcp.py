import os
import json
import re
import asyncio
import subprocess
from typing import Dict
from ...core.base_mcp import BaseMCP

class GoogleCalendarMCP(BaseMCP):
    """Implementación específica para el MCP de Google Calendar."""
    
    def __init__(self):
        super().__init__("google-calendar")
        
    async def setup(self, path: str, env_vars: Dict) -> bool:
        """Configura el MCP de Google Calendar."""
        try:
            # 1. Verificar credenciales mínimas para obtener token
            min_required = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']
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
            
            # 2. Crear archivo .env con las credenciales mínimas
            print("\nCreando archivo .env con credenciales básicas...")
            self.create_env_file(path, {k: v for k, v in env_vars.items() if k in min_required})
            print(f"Archivo .env creado en: {os.path.join(path, '.env')}")

            # 3. Modificar package.json para Windows
            print("\nModificando package.json para Windows...")
            package_path = os.path.join(path, 'package.json')
            if os.path.exists(package_path):
                with open(package_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                
                # Actualizar scripts y agregar dotenv
                package_data['scripts'] = {
                    "build": "tsc",
                    "start": "node build/index.js"
                }
                
                if 'dotenv' not in package_data.get('dependencies', {}):
                    package_data['dependencies']['dotenv'] = "^16.5.0"
                
                with open(package_path, 'w', encoding='utf-8') as f:
                    json.dump(package_data, f, indent=2)
                print("package.json actualizado para Windows")

            # 4. Instalar dependencias
            print("\nInstalando dependencias...")
            await self.run_command(f"cd {path} && npm install")

            # 5. Verificar si existe refresh token
            if not env_vars.get('GOOGLE_REFRESH_TOKEN', '').strip():
                print("\nNo se encontró refresh token.")
                print("Pasos a seguir:")
                print(" 1. Ejecuta en la terminal: node obtener_token_google.js")
                print(" 2. Completa el proceso de autenticación")
                print(" 3. Copia el refresh token generado")
                print(" 4. Actualiza el archivo repositories.json con el nuevo token")
                print(" 5. Elimina la carpeta del MCP google-calendar y vuelve a ejecutar python setup.py")
                return False

            # 6. Actualizar .env con todas las variables
            print("\nActualizando archivo .env con todas las variables...")
            self.create_env_file(path, env_vars)

            # 7. Modificar index.ts
            print("\nModificando index.ts...")
            index_path = os.path.join(path, 'index.ts')
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Agregar dotenv si no existe
                if "import * as dotenv from 'dotenv';" not in content:
                    content = content.replace(
                        "import { calendar_v3 } from '@googleapis/calendar';",
                        "import { calendar_v3 } from '@googleapis/calendar';\nimport * as dotenv from 'dotenv';\n\n// Cargar variables de entorno\ndotenv.config();\n"
                    )
                
                with open(index_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            print("index.ts actualizado")
            
            # 8. Compilar proyecto
            print("\nCompilando proyecto...")
            await self.run_command(f"cd {path} && npm run build")

            # 9. Modificar el archivo compilado
            print("\nModificando archivo compilado...")
            build_index_path = os.path.join(path, 'build', 'index.js')
            if os.path.exists(build_index_path):
                with open(build_index_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Agregar dotenv al archivo compilado
                if "import * as dotenv from 'dotenv';" not in content:
                    content = content.replace(
                        "import { google } from 'googleapis';",
                        "import { google } from 'googleapis';\nimport * as dotenv from 'dotenv';\n\n// Cargar variables de entorno\ndotenv.config();\n"
                    )
                
                with open(build_index_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print("Archivo compilado actualizado")
            
            # 10. Verificar que el servidor funcione
            print("\nVerificando que el servidor funcione...")
            if not await self.verify_server(path, env_vars):
                print("Error: El servidor no pudo iniciar correctamente")
                return False
            
            return True
                
        except Exception as e:
            print(f"Error configurando Google Calendar: {e}")
            return False
            
    def get_config(self) -> Dict:
        """Obtiene la configuración específica de Google Calendar para Claude Desktop."""
        return {
            "command": "node",
            "args":    ["build/index.js"],
            "env": {
                "GOOGLE_CLIENT_ID":     "",
                "GOOGLE_CLIENT_SECRET": "",
                "GOOGLE_REDIRECT_URI":  "",
                "GOOGLE_REFRESH_TOKEN": ""
            }
        }

    def create_env_file(self, path: str, env_vars: Dict) -> None:
        """Crea el archivo .env con las variables de entorno."""
        env_path = os.path.join(path, '.env')
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                f.write(f'{key}="{value}"\n')

    async def verify_server(self, path: str, env_vars: Dict) -> bool:
        """Verifica que el servidor funcione correctamente."""
        try:
            print("\nIntentando iniciar el servidor...")
            
            # Primero asegurarnos que el archivo .env está actualizado
            self.create_env_file(path, env_vars)
            
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
