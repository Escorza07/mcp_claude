# Requiere ejecución como administrador
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {  
    Write-Warning "Este script requiere privilegios de administrador. Por favor, ejecútalo como administrador."
    exit
}

# Función para actualizar la ruta de NSSM en default.properties
function Update-NssmPath {
    param (
        [string]$nssmExe
    )
    
    $content = Get-Content "$PSScriptRoot\..\config\default.properties"
    $newContent = @()
    $foundComment = $false
    
    foreach ($line in $content) {
        # Mantener líneas que no son rutas de dependencias
        if (-not ($line -match "^(NSSM_PATH)=")) {
            $newContent += $line
        }
        
        # Buscar el comentario de rutas
        if ($line -match "^# Rutas de dependencias instaladas") {
            $foundComment = $true
        }
    }
    
    # Si no se encontró el comentario, agregarlo al final
    if (-not $foundComment) {
        $newContent += ""
        $newContent += "# Rutas de dependencias instaladas"
    }
    
    # Agregar la ruta de NSSM
    $newContent += "NSSM_PATH=$nssmExe"
    
    Set-Content -Path "$PSScriptRoot\..\config\default.properties" -Value $newContent
}

# Configuración
$nssmVersion = "2.24"
$nssmUrl = "https://nssm.cc/ci/nssm-$nssmVersion.zip"
$nssmBasePath = "C:\nssm"
$nssmPath = "$nssmBasePath\nssm-$nssmVersion"

# Leer la ruta base de los repositorios desde default.properties
$defaultPropertiesPath = "$PSScriptRoot\..\config\default.properties"
if (-not (Test-Path $defaultPropertiesPath)) {
    Write-Host "Error: No se encontró el archivo default.properties en $defaultPropertiesPath"
    exit
}

$defaultProperties = Get-Content $defaultPropertiesPath
$repositoriesBasePath = ($defaultProperties | Where-Object { $_ -match "^REPOSITORIES_BASE_PATH=" } | Select-Object -First 1) -replace "REPOSITORIES_BASE_PATH=", ""
if (-not $repositoriesBasePath) {
    Write-Host "Error: No se encontró REPOSITORIES_BASE_PATH en default.properties"
    exit
}

# Construir la ruta del WhatsApp Bridge
$whatsappBridgePath = Join-Path $repositoriesBasePath "whatsapp-mcp\whatsapp-bridge"
$serviceName = "whatsapp-bridge"

# Función para encontrar nssm.exe
function Find-NssmExe {
    $possiblePaths = @(
        "$nssmPath\win64\nssm.exe",
        "$nssmBasePath\win64\nssm.exe",
        "$nssmBasePath\nssm.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

# Verificar si NSSM ya está instalado
$nssmExe = Find-NssmExe
if ($nssmExe) {
    Write-Host "NSSM ya está instalado en: $nssmExe"
    Update-NssmPath -nssmExe $nssmExe
} else {
    Write-Host "NSSM no encontrado. Descargando e instalando..."

# 1. Descargar e instalar NSSM
Write-Host "Descargando NSSM..."
    $tempFile = [System.IO.Path]::GetTempFileName() + ".zip"
    try {
Invoke-WebRequest -Uri $nssmUrl -OutFile $tempFile
        Write-Host "NSSM descargado exitosamente"
    } catch {
        Write-Host "Error al descargar NSSM: $_"
        Write-Host "Intentando usar la versión local si existe..."
    }

    # Extraer NSSM si se descargó correctamente
    if (Test-Path $tempFile) {
Write-Host "Extrayendo NSSM..."
        try {
            Expand-Archive -Path $tempFile -DestinationPath $nssmBasePath -Force
            Remove-Item $tempFile -ErrorAction SilentlyContinue
        } catch {
            Write-Host "Advertencia: No se pudo eliminar el archivo temporal. Esto es normal si NSSM está en uso."
        }
    }

    # Buscar nssm.exe después de la instalación
    $nssmExe = Find-NssmExe
    if (-not $nssmExe) {
        Write-Host "Error: No se pudo instalar NSSM correctamente."
        Write-Host "Por favor, instala NSSM manualmente de https://nssm.cc/download"
        exit
    }
    
    Update-NssmPath -nssmExe $nssmExe
}

# Verificar si el servicio ya está instalado
if (Get-Service $serviceName -ErrorAction SilentlyContinue) {
    Write-Host "`nEl servicio WhatsApp Bridge ya está instalado."
    Write-Host "Si deseas desinstalarlo, ejecuta:"
    Write-Host "nssm remove whatsapp-bridge confirm"
    Write-Host "`n¿Deseas continuar con la reinstalación? (S/N)"
    $response = Read-Host
    if ($response -ne "S") {
        exit
    }
    
    Write-Host "Desinstalando servicio existente..."
    & $nssmExe remove $serviceName confirm
    Start-Sleep -Seconds 2
}

# Agregar NSSM al PATH del sistema
$nssmDir = Split-Path -Parent $nssmExe
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if (-not $currentPath.Contains($nssmDir)) {
    Write-Host "Agregando NSSM al PATH del sistema..."
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$nssmDir", "Machine")
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine")
}

# 3. Compilar el bridge
Write-Host "`nCompilando WhatsApp Bridge..."
Set-Location $whatsappBridgePath
go build -o whatsapp-bridge.exe main.go

# 4. Instalar el servicio con configuración adicional
Write-Host "Instalando servicio de WhatsApp Bridge..."
& $nssmExe install $serviceName "$whatsappBridgePath\whatsapp-bridge.exe"

# Configurar el servicio
& $nssmExe set $serviceName AppDirectory "$whatsappBridgePath"
& $nssmExe set $serviceName DisplayName "WhatsApp Bridge Service"
& $nssmExe set $serviceName Description "Servicio para el puente de WhatsApp"
& $nssmExe set $serviceName Start SERVICE_AUTO_START
& $nssmExe set $serviceName AppStdout "$whatsappBridgePath\service.log"
& $nssmExe set $serviceName AppStderr "$whatsappBridgePath\service.log"
& $nssmExe set $serviceName AppRotateFiles 1
& $nssmExe set $serviceName AppRotateBytes 1048576

# 5. Iniciar el servicio
Write-Host "Iniciando servicio..."
try {
& $nssmExe start $serviceName
    Start-Sleep -Seconds 5  # Dar tiempo al servicio para iniciar
    
    # Verificar si el servicio está escuchando en el puerto 8080
    $portCheck = Test-NetConnection -ComputerName localhost -Port 8080
    if ($portCheck.TcpTestSucceeded) {
        Write-Host "¡Servicio iniciado exitosamente y escuchando en el puerto 8080!"
    } else {
        Write-Host "El servicio está corriendo pero no está escuchando en el puerto 8080"
        Write-Host "Revisa el archivo de log: $whatsappBridgePath\service.log"
    }
    
    $service = Get-Service $serviceName
    if ($service.Status -eq 'Running') {
        Write-Host "Estado del servicio: $($service.Status)"
    } else {
        Write-Host "El servicio no pudo iniciarse. Estado actual: $($service.Status)"
        Write-Host "Revisa el archivo de log: $whatsappBridgePath\service.log"
        Write-Host "Intenta reiniciar el servicio manualmente con: Restart-Service $serviceName"
    }
} catch {
    Write-Host "Error al iniciar el servicio: $_"
    Write-Host "Revisa el archivo de log: $whatsappBridgePath\service.log"
    Write-Host "Intenta iniciar el servicio manualmente con: Start-Service $serviceName"
}

Write-Host "`nPara verificar el estado del servicio, ejecuta: Get-Service $serviceName"
Write-Host "Para reiniciar el servicio: Restart-Service $serviceName"
Write-Host "Para detener el servicio: Stop-Service $serviceName"
Write-Host "Para desinstalar el servicio: nssm remove whatsapp-bridge confirm"
Write-Host "Para ver los logs: Get-Content $whatsappBridgePath\service.log" 