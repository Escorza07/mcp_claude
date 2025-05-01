# MCP Claude - Sistema de Integración de Servicios

Este proyecto integra múltiples servicios a través de MCPs (Microservicios de Control de Procesos). Los MCPs se dividen en dos tipos:

1. **Servidores Físicos**: Son servicios que se instalan y ejecutan localmente en tu máquina:
   - Google Calendar
   - Gmail
   - Trello
   - WhatsApp
   - LinkedIn

2. **Servidores Temporales**: Son servicios que se ejecutan bajo demanda y se cierran automáticamente:
   - brave-search
   - filesystem
   - memory
   - puppeteer
   - fetch

## Requisitos Previos

- Windows 10 o superior
- PowerShell (ejecutar como administrador)
- Conexión a internet
- Cuentas en los servicios a integrar (Google, Trello, etc.)

## Instalación

### 1. Configuración Inicial

1. Clona este repositorio en la ubicación deseada:
```powershell
git clone [URL_DEL_REPOSITORIO]
```

2. Configura la ruta base para los repositorios en `config/default.properties`:
```
REPOSITORIES_BASE_PATH=C:/ruta/deseada/para/mcps
```
### 2. Configuración de Variables de Entorno

1. Crea un archivo `.env` en la carpeta `config/` basado en el siguiente formato de .env.example y pon ahi tus credenciales, si no se tiene el refresh token lo puedes obtener en el paso 4.

### 3. Instalación de Dependencias

1. Debes instalar manualmente el compilador GCC (útil para compilar módulos nativos de Node.js y otras dependencias que requieren compilación), ejecuta:
```
.\tdm64-gcc-10.3.0-2.exe
```

2. Ve a donde clonaste el repositorio, entra en el proyecto clonado y ejecuta el script de instalación de dependencias como administrador:
```powershell
.\scripts\install_dependencies.ps1
```

3. Para verificar que todo se ha instalado correctamente debe haber un conjunto de rutas en el archivo default.properties.

4. Si por equivocacion primero ejecutaste .\scripts\install_dependencies.ps1 te recomendara primero instalar el gcc para que se considere las instlaciones exitosas, entonces cierra el powershell, ejecuta (tdm64-gcc-10.3.0-2.exe) y luego vuelve a ejcutar .\scripts\install_dependencies.ps1 en powershell, ahora si las rutas deberian aparecer en default.properties.

### 4. Configuración de Autenticación Google

1. Si no tienes un refresh token de Google, ejecuta:
```powershell
.\scripts\setup_google_auth.ps1
```

2. Sigue las instrucciones en pantalla para autorizar la aplicación.
3. El script generará automáticamente el archivo `google_auth.json` y actualizará el refresh token en el archivo `.env`, si no ves que se actualizo en el archivo .env, hazlo manualmente.

### 5. Instalación de MCPs

1. Ejecuta el script de instalación:
```powershell
python setup.py
```

2. Este script:
   - Clonará todos los repositorios MCP necesarios
   - Te pedira confirmacion para descargar los mcp no fisicos.
   - Instalará las dependencias de cada MCP
   - Configurará las variables de entorno

### 6. Configuración de WhatsApp

1. Abre un cmd en la siguiente ruta:
```
cd %REPOSITORIES_BASE_PATH%/whatsapp-mcp/whatsapp-bridge
 y ejecuta: 
go run main.go
```

2. Escanea el código QR que aparece en la terminal con tu teléfono y esperar que termine de sincronizar los mensajes.

3. Para evitar tener que mantener una terminal abierta, instala el servicio de WhatsApp:
```powershell
.\scripts\setup_whatsapp_service.ps1
```

Este servicio se ejecutará en segundo plano y mantendrá la sesión de WhatsApp activa.

## Estructura del Proyecto

```
mcp_claude/
├── config/
│   ├── .env                    # Variables de entorno
│   ├── default.properties      # Configuración general
│   ├── google_auth.json        # Tokens de Google
│   └── repositories.json       # Configuración de MCPs
├── scripts/
│   ├── install_dependencies.ps1
│   ├── setup_google_auth.ps1
│   └── setup_whatsapp_service.ps1
└── src/                        # Código fuente principal
```

## Servicios Disponibles

### Servidores Físicos
- **Google Calendar**: Gestión de eventos y calendarios, permite crear, modificar y eliminar eventos en tu calendario de Google.
- **Gmail**: Gestión de correos electrónicos, permite enviar, recibir y gestionar correos desde tu cuenta de Gmail.
- **Trello**: Gestión de tableros y tarjetas, permite crear y gestionar tareas en tus tableros de Trello.
- **WhatsApp**: Mensajería y automatización, permite enviar y recibir mensajes de WhatsApp de forma automatizada.
- **LinkedIn**: Extracción de datos, permite obtener información de perfiles y empresas de LinkedIn.

### Servidores Temporales
- **brave-search**: Motor de búsqueda que utiliza la API de Brave para realizar búsquedas en internet.
- **filesystem**: Acceso al sistema de archivos local, permite leer y escribir archivos en tu computadora.
- **memory**: Gestión de memoria temporal, permite almacenar y recuperar datos durante la sesión.
- **puppeteer**: Automatización de navegadores web, permite controlar un navegador Chrome/Chromium.
- **fetch**: Servicio de obtención de datos, permite realizar peticiones HTTP y procesar respuestas.

## Solución de Problemas

### Problemas Comunes

1. **Error en la clonación de MCPs físicos**:
   - Si hay un error durante la clonación de un MCP físico (Google Calendar, Gmail, Trello, WhatsApp o LinkedIn), deberás:
     1. Eliminar manualmente la carpeta del MCP en la ruta configurada en `REPOSITORIES_BASE_PATH`
     2. Ejecutar nuevamente `python setup.py`
   - Esto es necesario porque el sistema verifica la existencia de la carpeta para determinar si un MCP ya está instalado
   - Si la carpeta existe, el sistema asumirá que el MCP está correctamente instalado y no intentará clonarlo nuevamente
   - Solo eliminando la carpeta podrás forzar una nueva clonación y configuración del MCP

2. **borrar carpeta whatsapp**:
   - Si hay un error en la instalacion de algun mcp y deseas instalarlo de nuevo, recuerda eliminar la carpeta para que se vuelva a clonar nuevamente
   - recuerda que a veces te dira que no puede borrarla y es porque esta siendo utiliza, ya sea por powershell, un cmd, etc
   - el mcp de whatsapp utiliza entornos, entonces para eliminar primero ejecuta: 
   taskkill /F /IM python.exe luego ya se podra eliminar la carpeta

3. **Error al encontrar el archivo .env**:
   - Asegúrate de que el archivo existe en `config/.env`
   - Verifica los permisos de lectura
   - Comprueba que sea .env, a veces no se tiene activo el visor de extensiones
   - puede verse como .env, pero de manera oculta esta .env.txt u otra forma.
   - debes elminar cualquier extension y solo debe estar .env

4. **Error en la instalación de dependencias**:
   - Ejecuta el instalador de GCC si se solicita
   - Verifica que tienes permisos de administrador
   - Asegúrate de tener conexión a internet

5. **Problemas con la autenticación de Google**:
   - Verifica que las credenciales en `.env` son correctas
   - Ejecuta `setup_google_auth.ps1` para renovar los tokens

6. **WhatsApp no mantiene la sesión**:
   - Asegúrate de que el servicio está instalado correctamente
   - Verifica que el servicio está en ejecución en los servicios de Windows
   - el servicio se whatsapp-bridge
   -si vuelves a ejecutar .\scripts\setup_whatsapp_service.ps1 recuerda eliminar primero el servicio antiguo con el siguiente comando: nssm remove whatsapp-bridge confirm
   - si te salen errores de que no puede escuchar el puerto, es porque otro servicio lo esta usando.

7. **no funciona go run main.go**:
   - Aveces algun antivirus toma el archivo main.exe y lo pone en cuarentena tomandolo como amenaza
   - Restaura el main .exe y quitalo de cuarentena

8. **error en brave ${APPDATA}**:
   - abre un cmd y ejecuta npm i @modelcontextprotocol/server-brave-search, vuelve a abrir claude desde 0.
   
## Mantenimiento

- Para actualizar los MCPs, ejecuta `python setup.py` nuevamente
- Para renovar tokens de Google, ejecuta `setup_google_auth.ps1`
- Para reiniciar el servicio de WhatsApp, usa el administrador de servicios de Windows

## Contribución

Si deseas contribuir al proyecto, por favor:
1. Haz un fork del repositorio
2. Crea una rama para tu feature
3. Envía un pull request con tus cambios

## Licencia

Este proyecto está bajo la licencia [LICENCIA]. Consulta el archivo LICENSE para más detalles. 