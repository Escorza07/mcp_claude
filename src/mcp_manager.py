import os
import json
import asyncio
from typing import Dict, List, Optional
from .mcps.trello.trello_mcp import TrelloMCP
from .mcps.google_calendar.google_calendar_mcp import GoogleCalendarMCP
from .mcps.gmail.gmail_mcp import GmailMCP
from .mcps.whatsapp.whatsapp_mcp import WhatsAppMCP
from .mcps.linkedin_extract.linkedin_extract_mcp import LinkedInMCP

# Lista de MCPs NPX con sus configuraciones específicas
NPX_MCPS = {
    "brave-search": {
        "package": "@modelcontextprotocol/server-brave-search",
        "env": {"BRAVE_API_KEY": ""}
    },
    "filesystem": {
        "package": "@modelcontextprotocol/server-filesystem",
        "args": [
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "Downloads")
        ]
    },
    "memory": {
        "package": "@modelcontextprotocol/server-memory"
    },
    "puppeteer": {
        "package": "@modelcontextprotocol/server-puppeteer"
    }
}

# Lista de MCPs UVX
UVX_MCPS = {
    "fetch": {
        "package": "mcp-server-fetch"
    }
}

class MCPManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self.load_config(config_path)
        self.base_path = self.config['base_path']
        self.mcp_handlers = {
            'trello': TrelloMCP(),
            'google-calendar': GoogleCalendarMCP(),
            'gmail': GmailMCP(),
            'linkedin-extract': LinkedInMCP(),
            'whatsapp': WhatsAppMCP(),
        }
        self.env_vars = self.load_env_vars()
        
    def load_config(self, config_path: str) -> Dict:
        """Carga la configuración desde el archivo repositories.json y reemplaza las variables de entorno."""
        try:
            # Primero cargar default.properties
            default_props = {}
            with open('config/default.properties', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        default_props[key.strip()] = value.strip()

            # Cargar repositories.json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Reemplazar la ruta base con la de default.properties
            if 'base_path' in config and 'REPOSITORIES_BASE_PATH' in default_props:
                config['base_path'] = default_props['REPOSITORIES_BASE_PATH']

            # Cargar variables de entorno desde .env
            env_vars = {}
            env_path = os.path.join(os.path.dirname(config_path), '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip('"\' ')

            # Reemplazar variables de entorno en los repositorios
            for repo in config.get('repositories', []):
                if 'env_vars' in repo:
                    for key, value in repo['env_vars'].items():
                        if value.startswith('%') and value.endswith('%'):
                            env_key = value[1:-1]
                            if env_key in env_vars:
                                repo['env_vars'][key] = env_vars[env_key]

            return config
        except Exception as e:
            print(f"Error cargando configuración: {str(e)}")
            return {}
            
    def load_env_vars(self) -> Dict:
        """Carga las variables de entorno desde config/.env"""
        env_vars = {}
        env_path = os.path.join(os.path.dirname(self.config_path), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key] = value.strip('"\'')
        return env_vars

    async def run_command(self, command: str) -> bool:
        """Ejecuta un comando en la terminal."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_message = stderr.decode().strip()
                print(f"Error ejecutando comando: {error_message}")
                return False

            output = stdout.decode().strip()
            if output:
                print(output)

            return True
        except Exception as e:
            print(f"Error ejecutando comando: {str(e)}")
            return False

    async def install_npx_packages(self):
        """Instala el paquete NPX de brave-search"""
        print("\n=== Instalación de paquete NPX ===")
        respuesta = input("\n¿Deseas instalar el paquete NPX de brave-search ahora? (s/n): ").lower()
        if respuesta != 's':
            print("Omitiendo instalación de paquete NPX...")
            return

        # Cambiar al directorio del usuario
        user_dir = os.path.expanduser("~")
        os.chdir(user_dir)
        print(f"\nInstalando en: {user_dir}")

        print("\nInstalando @modelcontextprotocol/server-brave-search...")
        try:
            await self.run_command("npm i @modelcontextprotocol/server-brave-search")
            print("Paquete instalado correctamente")
        except Exception as e:
            print(f"Error instalando el paquete: {e}")

    async def setup_all_mcps(self):
        """Configura todos los MCPs listados en la configuración."""
        # Crear directorio base si no existe
        os.makedirs(self.base_path, exist_ok=True)
        
        # Instalar paquetes NPX
        await self.install_npx_packages()
        
        # Lista para guardar los MCPs instalados
        installed_mcps = []
        failed_mcps = []
        
        # Configurar cada MCP secuencialmente
        for repo in self.config['repositories']:
            try:
                # 1. Extraer información del repositorio
                repo_name = repo['url'].split('/')[-1].replace('.git', '')
                target_path = os.path.join(self.base_path, repo_name)
                
                # 2. Verificar si ya está configurado
                is_configured = os.path.exists(target_path)
                
                if is_configured:
                    print(f"MCP {repo_name} ya está configurado. Saltando...")
                    installed_mcps.append(repo_name)
                    continue
                
                print(f"\nConfigurando MCP en: {target_path}")
                
                # 3. Clonar repositorio
                print(f"Clonando repositorio: {repo['url']}")
                if not await self.clone_repository(repo['url'], target_path):
                    print(f"Error al clonar el repositorio {repo_name}. Saltando...")
                    failed_mcps.append(repo_name)
                    continue
                
                # 4. Verificar si el repositorio tiene una subcarpeta con el mismo nombre
                subfolder_path = os.path.join(target_path, repo_name)
                if os.path.exists(subfolder_path):
                    print(f"Configurando en subcarpeta: {subfolder_path}")
                    target_path = subfolder_path
                
                # 5. Determinar el tipo de MCP y configurarlo
                mcp_type = None
                if 'trello' in repo_name.lower():
                    mcp_type = 'trello'
                elif 'google-calendar' in repo_name.lower():
                    mcp_type = 'google-calendar'
                elif 'gmail' in repo_name.lower():
                    mcp_type = 'gmail'
                elif 'linkedin-extract' in repo_name.lower():
                    mcp_type = 'linkedin-extract'
                elif 'whatsapp' in repo_name.lower():
                    mcp_type = 'whatsapp'

                
                if mcp_type and mcp_type in self.mcp_handlers:
                    print(f"\nConfigurando MCP de {mcp_type}...")
                    if await self.mcp_handlers[mcp_type].setup(target_path, repo.get('env_vars', {})):
                        installed_mcps.append(repo_name)
                    else:
                        failed_mcps.append(repo_name)
                else:
                    print(f"No se pudo determinar el tipo de MCP para {repo_name}")
                    failed_mcps.append(repo_name)
                    
            except Exception as e:
                print(f"Error configurando MCP {repo_name}: {str(e)}")
                failed_mcps.append(repo_name)
                continue
                
        if installed_mcps or NPX_MCPS or UVX_MCPS:
            print("\n=== Resumen de MCPs instalados ===")
            
            # Mostrar MCPs físicos
            for mcp in installed_mcps:
                print(f"- {mcp}")
            
            # Mostrar MCPs NPX
            for mcp_name in NPX_MCPS:
                print(f"- {mcp_name} (con npx)")
            
            # Mostrar MCPs UVX
            for mcp_name in UVX_MCPS:
                print(f"- {mcp_name} (con uvx)")
            
            print("================================")
            
            if failed_mcps:
                print("\n=== MCPs que fallaron ===")
                for mcp in failed_mcps:
                    print(f"- {mcp}")
                print("================================")
                print("\nNo se actualizará el archivo de configuración hasta que todos los MCPs se configuren correctamente.")
            else:
                print("\nTodas las MCPs se han configurado correctamente.")
                print("Actualizando archivo de configuración para Claude Desktop...")
                self.create_claude_desktop_config(installed_mcps)
                
    async def clone_repository(self, url: str, path: str) -> bool:
        try:
            if os.path.exists(path):
                print(f"El directorio {path} ya existe. Saltando clonación...")
                return True

            command = f"git clone {url} {path}"
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_message = stderr.decode().strip()
                if "already exists" in error_message:
                    print(f"El repositorio ya existe en {path}")
                    return True
                else:
                    print(f"Error al clonar el repositorio: {error_message}")
                    return False

            output = stdout.decode().strip()
            if output:
                print(output)

            return True

        except Exception as e:
            print(f"Error al clonar el repositorio: {str(e)}")
            return False

    def create_claude_desktop_config(self, installed_mcps: List[str]):
        try:
            config = { "mcpServers": {} }

            # Agregar MCPs NPX
            for mcp_name, mcp_config in NPX_MCPS.items():
                config["mcpServers"][mcp_name] = {
                    "command": "npx",
                    "args": ["-y", mcp_config["package"]]
                }
                
                if "args" in mcp_config:
                    config["mcpServers"][mcp_name]["args"].extend(mcp_config["args"])
                    
                if "env" in mcp_config:
                    # Si es brave-search, usar la clave del archivo .env
                    if mcp_name == "brave-search" and "BRAVE_API_KEY" in self.env_vars:
                        config["mcpServers"][mcp_name]["env"] = {
                            "BRAVE_API_KEY": self.env_vars["BRAVE_API_KEY"]
                        }
                    else:
                        config["mcpServers"][mcp_name]["env"] = mcp_config["env"]

            # Agregar MCP fetch con configuración específica
            config["mcpServers"]["fetch"] = {
                "command": "uvx",
                "args": ["mcp-server-fetch"]
            }

            # Agregar MCPs físicos
            for mcp_name in installed_mcps:
                mcp_path = os.path.join(self.base_path, mcp_name)
                
                subfolder_path = os.path.join(mcp_path, mcp_name)
                if os.path.exists(subfolder_path):
                    mcp_path = subfolder_path

                mcp_type = None
                if 'trello' in mcp_name.lower():
                    mcp_type = 'trello'
                elif 'google-calendar' in mcp_name.lower():
                    mcp_type = 'google-calendar'
                elif 'gmail' in mcp_name.lower():
                    mcp_type = 'gmail'
                elif 'whatsapp' in mcp_name.lower():
                    mcp_type = 'whatsapp'
                elif 'linkedin-extract' in mcp_name.lower():
                    mcp_type = 'linkedin-extract'

                if mcp_type and mcp_type in self.mcp_handlers:
                    mcp_config = self.mcp_handlers[mcp_type].get_config()
                    
                    if mcp_type != 'whatsapp':  # Solo modificar rutas para MCPs que no sean WhatsApp
                        build_path = os.path.join(mcp_path, mcp_config['args'][0])
                        if os.path.exists(build_path):
                            mcp_config['args'][0] = build_path.replace("\\", "/")
                        else:
                            mcp_config['args'][0] = os.path.join(mcp_path, mcp_config['args'][0]).replace("\\", "/")

                    for repo in self.config['repositories']:
                        repo_name = repo['url'].split('/')[-1].replace('.git', '')
                        if repo_name == mcp_name and 'env_vars' in repo:
                            mcp_config['env'] = repo['env_vars']
                            break

                    # Asegurar que todas las rutas en la configuración usen barras normales
                    if 'command' in mcp_config:
                        mcp_config['command'] = mcp_config['command'].replace("\\", "/")
                    if 'args' in mcp_config:
                        mcp_config['args'] = [arg.replace("\\", "/") if isinstance(arg, str) else arg for arg in mcp_config['args']]

                    config["mcpServers"][mcp_type] = mcp_config

            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, "claude_desktop_config.json")
            
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            if os.path.exists(config_path):
                print("Archivo de configuración creado exitosamente.")
                print("\nPor favor, copia el archivo 'claude_desktop_config.json' en donde tengas instalado Claude Desktop")
            else:
                print("Error: No se pudo crear el archivo de configuración.")
                
        except Exception as e:
            print(f"Error al crear/actualizar el archivo de configuración: {str(e)}")

    def _get_mcp_config(self, mcp_name: str) -> Optional[Dict]:
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config.get(mcp_name)
        except Exception as e:
            print(f"Error al leer configuración de {mcp_name}: {str(e)}")
            return None
