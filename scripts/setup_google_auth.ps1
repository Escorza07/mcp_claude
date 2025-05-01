# Requiere ejecución como administrador
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {  
    Write-Warning "Este script requiere privilegios de administrador. Por favor, ejecútalo como administrador."
    exit
}

# Configuración
$scriptPath = $PSScriptRoot
$googleAuthPath = Join-Path $scriptPath "google_auth.js"

# Verificar si existe el script de autenticación
if (-not (Test-Path $googleAuthPath)) {
    Write-Host "Error: No se encontró el script de autenticación de Google."
    Write-Host "Por favor, asegúrate de que el archivo google_auth.js existe en la carpeta scripts."
    exit
}

# Instalar dependencias si es necesario
Write-Host "Verificando dependencias..."
if (-not (Test-Path (Join-Path $scriptPath "node_modules"))) {
    Write-Host "Instalando dependencias..."
    npm install googleapis
}

# Ejecutar script de autenticación
Write-Host "`nIniciando proceso de autenticación de Google..."
Write-Host "Este proceso solicitará permisos para:"
Write-Host "- Google Calendar"
Write-Host "- Gmail"
Write-Host "`nSigue las instrucciones en pantalla para completar la autenticación."
Write-Host "Presiona Enter para continuar..."
Read-Host

node $googleAuthPath

Write-Host "`nProceso de autenticación completado."
Write-Host "Si necesitas actualizar los MCPs con el nuevo token, ejecuta:"
Write-Host "python setup.py" 