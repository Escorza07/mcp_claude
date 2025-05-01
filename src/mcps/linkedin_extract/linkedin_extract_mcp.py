import os
import json
import asyncio
import subprocess
from typing import Dict
from ...core.base_mcp import BaseMCP

class LinkedInMCP(BaseMCP):
    """Implementación específica para el MCP de LinkedIn."""
    
    def __init__(self):
        super().__init__("linkedin-extract")
        
    async def setup(self, path: str, env_vars: Dict) -> bool:
        """Configura el MCP de LinkedIn."""
        try:
            # 1. Verificar credenciales mínimas
            min_required = ['APIFY_TOKEN']
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

            # 3. Modificar package.json
            print("\nModificando package.json...")
            package_json_path = os.path.join(path, 'package.json')
            if os.path.exists(package_json_path):
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_json = json.load(f)
                
                if 'scripts' in package_json and 'build' in package_json['scripts']:
                    package_json['scripts']['build'] = 'tsc'
                    
                with open(package_json_path, 'w', encoding='utf-8') as f:
                    json.dump(package_json, f, indent=2)
                print("package.json actualizado correctamente")

            # 4. Instalar dependencias
            print("\nInstalando dependencias...")
            await self.run_command(f"cd {path} && npm install")

            # 5. Construir el proyecto
            print("\nConstruyendo el proyecto...")
            await self.run_command(f"cd {path} && npm run build")

            # 6. Configurar config.js
            print("\nConfigurando config.js...")
            config_js_path = os.path.join(path, 'build', 'config.js')
            if os.path.exists(config_js_path):
                with open(config_js_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = 'import dotenv from \'dotenv\';\ndotenv.config();\n\n' + content
                
                with open(config_js_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print("config.js actualizado correctamente")
            else:
                print("Error: No se encontró el archivo config.js en la carpeta build")
                return False

            # 7. Verificar que el servidor funciona
            print("\nVerificando que el servidor funciona...")
            if not await self.verify_server(path):
                print("Error: El servidor no pudo iniciar correctamente")
                return False
            
            return True
                
        except Exception as e:
            print(f"Error configurando LinkedIn: {e}")
            return False
            
    def get_config(self) -> Dict:
        """Obtiene la configuración específica de LinkedIn para Claude Desktop."""
        return {
            "command": "node",
            "args": ["build/index.js"],
            "env": {
                "APIFY_TOKEN": ""
            }
        }

    def create_env_file(self, path: str, env_vars: Dict) -> None:
        """Crea el archivo .env con las variables de entorno."""
        env_path = os.path.join(path, '.env')
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                f.write(f'{key}="{value}"\n') 