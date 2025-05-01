# Ocultar la salida del código
$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference = "SilentlyContinue"

# Función para leer propiedades
function Get-PropertyValue {
    param (
        [string]$filePath,
        [string]$propertyName
    )
    $content = Get-Content $filePath
    $line = $content | Where-Object { $_ -match "^$propertyName\s*=\s*(.+)$" }
    if ($line) {
        return $matches[1]
    }
    return $null
}

# Función para actualizar default.properties con las rutas de instalación
function Update-PropertiesFile {
    param (
        [string]$filePath,
        [hashtable]$properties
    )
    
    $content = Get-Content $filePath
    $newContent = @()
    $foundComment = $false
    
    foreach ($line in $content) {
        # Mantener líneas que no son rutas de dependencias
        if (-not ($line -match "^(NODE_PATH|GO_PATH|CHOCO_PATH|PYTHON_PATH|UV_PATH|NSSM_PATH)=")) {
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
    
    # Agregar las rutas después del comentario
    foreach ($key in $properties.Keys) {
        if ($key -match "^(NODE_PATH|GO_PATH|CHOCO_PATH|PYTHON_PATH|UV_PATH|NSSM_PATH)$") {
            $newContent += "$key=$($properties[$key])"
        }
    }
    
    Set-Content -Path $filePath -Value $newContent
}

# Leer configuraciones de default.properties
$configPath = "config/default.properties"
$nodeVersion = Get-PropertyValue -filePath $configPath -propertyName "node_version"
$repositoriesPath = Get-PropertyValue -filePath $configPath -propertyName "REPOSITORIES_BASE_PATH"

# Verificar si se está ejecutando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Por favor, ejecuta este script como administrador"
    exit 1
}

# Función para actualizar el PATH
function Update-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Función para verificar si nvm está instalado
function Test-NvmInstalled {
    try {
        $nvmVersion = nvm version
        return $true
    } catch {
        return $false
    }
}

# Función para verificar la versión de Node.js
function Test-NodeVersion {
    try {
        $nodeVersion = node --version
        $versionNumber = [version]($nodeVersion -replace 'v', '')
        $minVersion = [version]"18.0.0"
        return $versionNumber -ge $minVersion
    } catch {
        return $false
    }
}

# Función para reinstalar Chocolatey
function Reinstall-Chocolatey {
    Write-Host "Reinstalando Chocolatey..."
    Remove-Item -Path "$env:ChocolateyInstall" -Recurse -Force -ErrorAction SilentlyContinue
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
    Update-Path
}

# Verificar e instalar Chocolatey
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
    Update-Path
}

# Verificar si nvm está instalado y tiene Node.js
$nvmInstalled = Test-NvmInstalled
$nodeVersionOk = Test-NodeVersion

if ($nvmInstalled) {
    Write-Host "nvm detectado. Usando nvm para gestionar Node.js..."
    
    if (-not $nodeVersionOk) {
        Write-Host "Instalando Node.js 18.17.0 con nvm..."
        nvm install 18.17.0
        nvm use 18.17.0
        nvm alias default 18.17.0
        Update-Path
        refreshenv
    } else {
        Write-Host "Node.js versión compatible detectada con nvm"
    }
} else {
    Write-Host "nvm no detectado. Usando Chocolatey para instalar Node.js..."
    
    # Verificar e instalar Node.js
    Write-Host "Verificando Node.js..."
    $currentNodeVersion = node -v
    if (-not $currentNodeVersion) {
        Write-Host "Node.js no detectado. Instalando Node.js $nodeVersion..."
        
        # Limpiar la caché de Chocolatey
        Write-Host "Limpiando caché de Chocolatey..."
        choco cache remove --all -y
        
        # Instalar Node.js con parámetros específicos
        Write-Host "Instalando Node.js..."
        try {
            choco install nodejs --version=$nodeVersion -y --force --install-arguments="'/l*v c:\nodejs_install.log'"
        } catch {
            Write-Host "Error al instalar Node.js. Reinstalando Chocolatey..."
            Reinstall-Chocolatey
            choco install nodejs --version=$nodeVersion -y --force --install-arguments="'/l*v c:\nodejs_install.log'"
        }
        
        # Actualizar PATH
        Update-Path
        refreshenv
        
        # Verificar instalación
        $currentNodeVersion = node -v
        if (-not $currentNodeVersion) {
            Write-Host "Error: No se pudo instalar Node.js. Intentando método alternativo..."
            
            # Intentar con nodejs.install
            Write-Host "Intentando con nodejs.install..."
            try {
                choco install nodejs.install --version=$nodeVersion -y --force --install-arguments="'/l*v c:\nodejs_install.log'"
            } catch {
                Write-Host "Error al instalar Node.js.install. Reinstalando Chocolatey..."
                Reinstall-Chocolatey
                choco install nodejs.install --version=$nodeVersion -y --force --install-arguments="'/l*v c:\nodejs_install.log'"
            }
            
            # Actualizar PATH nuevamente
            Update-Path
            refreshenv
            
            # Verificar instalación nuevamente
            $currentNodeVersion = node -v
            if (-not $currentNodeVersion) {
                Write-Host "Error: No se pudo instalar Node.js. Por favor:"
                Write-Host "1. Reinicia tu computadora"
                Write-Host "2. Abre PowerShell como administrador"
                Write-Host "3. Ejecuta: choco install nodejs --version=$nodeVersion -y"
                exit 1
            }
        }
    } else {
        Write-Host "Node.js versión $currentNodeVersion detectada (OK)"
    }
}

# Verificar e instalar npm
Write-Host "`nVerificando npm..."
$npmVersion = npm -v
if (-not $npmVersion) {
    Write-Host "npm no detectado. Intentando reinstalar Node.js..."
    
    # Reinstalar Node.js
    Write-Host "Desinstalando Node.js..."
    choco uninstall nodejs -y --force
    Write-Host "Instalando Node.js nuevamente..."
    choco install nodejs --version=20.11.1 -y --force
    
    # Actualizar PATH
    Update-Path
    refreshenv
    
    # Verificar npm nuevamente
    $npmVersion = npm -v
    if (-not $npmVersion) {
        Write-Host "Error: No se pudo instalar npm. Por favor:"
        Write-Host "1. Reinicia tu computadora"
        Write-Host "2. Abre PowerShell como administrador"
        Write-Host "3. Ejecuta: choco install nodejs --version=20.11.1 -y"
        exit 1
    }
} else {
    Write-Host "npm versión $npmVersion detectada (OK)"
}

# Instalar Python si no está instalado
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando Python..."
    
    # Instalar Python usando el instalador oficial
    $pythonUrl = "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"
    
    Write-Host "Descargando instalador de Python..."
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath
    
    Write-Host "Instalando Python..."
    Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
    
    # Limpiar el instalador
    Remove-Item $installerPath -Force
    
    # Actualizar PATH
    Update-Path
    Start-Sleep -Seconds 10
}

# Crear y configurar entorno virtual de Python
Write-Host "`nConfigurando entorno virtual de Python..." -ForegroundColor Cyan
$venv_path = "venv"
if (-not (Test-Path $venv_path)) {
    Write-Host "Creando entorno virtual en $venv_path..."
    python -m venv $venv_path
}

# Activar el entorno virtual
Write-Host "Activando entorno virtual..."
& "$venv_path\Scripts\Activate.ps1"

# Instalar dependencias de Python
Write-Host "Instalando dependencias de Python..."
pip install -r requirements.txt

# Verificar e instalar Go
Write-Host "`nVerificando Go..."
if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando Go..."
    choco install golang -y
    Update-Path
    refreshenv
}

# Verificar versión de Go
$goVersion = go version
if (-not $goVersion) {
    Write-Host "Error: No se pudo instalar Go. Por favor:"
    Write-Host "1. Reinicia tu computadora"
    Write-Host "2. Abre PowerShell como administrador"
    Write-Host "3. Ejecuta: choco install golang -y"
    exit 1
} else {
    Write-Host "Go versión $goVersion detectada (OK)"
}

# Verificar e instalar TDM-GCC
Write-Host "`nVerificando TDM-GCC..."
$gccPaths = @(
    "C:\TDM-GCC-64\bin",
    "C:\MinGW\bin",
    "C:\MinGW64\bin",
    "C:\Program Files\TDM-GCC-64\bin",
    "C:\Program Files (x86)\TDM-GCC-64\bin"
)

$gccFound = $false
foreach ($path in $gccPaths) {
    if (Test-Path $path) {
        $gccPath = $path
        $gccFound = $true
        Write-Host "TDM-GCC encontrado en: $path"
        break
    }
}

if (-not $gccFound) {
    Write-Host "`nTDM-GCC no detectado. Por favor instálalo manualmente siguiendo estos pasos:"
    Write-Host "3. Ejecuta tdm64-gcc-10.3.0-2.exe que se encuentra dentro del proyecto"
    Write-Host "2. Si no se encuentra visita https://sourceforge.net/projects/tdm-gcc/files/v10.3.0-tdm64-2/tdm64-gcc-10.3.0-2.exe/download"
    Write-Host "3. Descarga el archivo tdm64-gcc-10.3.0-2.exe"
    Write-Host "4. Ejecuta el instalador con los valores por defecto"
    Write-Host "5. Abre una nueva ventana de PowerShell como administrador"
    Write-Host "6. Ejecuta el script nuevamente"
    Write-Host "7. si hay problemas reinicia tu computadora "
    Write-Host "7. Se considera todo en orden cuando en default.properties se ven las rutas de las instalaciones "
    exit 1
}

if ($gccFound) {
    # Agregar al PATH si no está
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if (-not $currentPath.Contains($gccPath)) {
        Write-Host "Agregando TDM-GCC al PATH del sistema..."
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$gccPath", "Machine")
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine")
    }
    
    # Verificar instalación
    try {
        $gccVersion = & "$gccPath\gcc.exe" --version
        if ($gccVersion) {
            Write-Host "TDM-GCC versión detectada (OK)"
            Write-Host $gccVersion
        } else {
            Write-Host "Error: TDM-GCC instalado pero no funciona correctamente"
            Write-Host "Por favor, reinicia tu computadora y ejecuta el script nuevamente"
            exit 1
        }
    } catch {
        Write-Host "Error al ejecutar gcc: $_"
        Write-Host "Por favor, reinicia tu computadora y ejecuta el script nuevamente"
        exit 1
    }
}

# Instalar UV (gestor de paquetes de Python)
Write-Host "`nInstalando UV (gestor de paquetes de Python)..."
try {
    # Desactivar temporalmente el entorno virtual si está activo
    if ($env:VIRTUAL_ENV) {
        Write-Host "Desactivando entorno virtual temporalmente..."
        deactivate
    }
    
    # Obtener la ubicación de Python y el directorio de scripts del usuario
    $pythonPath = (Get-Command python).Source
    $pythonDir = Split-Path -Parent $pythonPath
    $userScriptsDir = Join-Path $env:APPDATA "Python\Scripts"
    $pythonScriptsDir = Join-Path $pythonDir "Scripts"
    
    # Instalar UV globalmente
    Write-Host "Instalando UV globalmente..."
    python -m pip install --user uv
    
    # Verificar instalación en múltiples ubicaciones posibles
    $uvLocations = @(
        (Join-Path $env:APPDATA "Python\Python311\site-packages"),
        (Join-Path $env:APPDATA "Python\Python311\Scripts"),
        $pythonScriptsDir,
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\Scripts")
    )
    
    $uvPath = $null
    foreach ($location in $uvLocations) { 
        $potentialPath = Join-Path $location "uv.exe"
        if (Test-Path $potentialPath) {
            $uvPath = $potentialPath
            Write-Host "UV encontrado en: $location"
            break
        }
    }
    
    if (-not $uvPath) {
        Write-Host "Error: No se pudo encontrar UV después de la instalación"
        Write-Host "Ubicaciones verificadas:"
        foreach ($location in $uvLocations) {
            Write-Host "- $location"
        }
        Write-Host "`nPor favor, instala UV manualmente:"
        Write-Host "python -m pip install --user uv"
        Write-Host "Y luego agrega el directorio de scripts de Python al PATH"
        exit 1
    }
    
    # Agregar el directorio de UV al PATH si no está
    $uvDir = Split-Path -Parent $uvPath
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $currentPath.Contains($uvDir)) {
        Write-Host "Agregando directorio de UV al PATH..."
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$uvDir", "User")
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "User")
    }
    
    # Reactivar el entorno virtual si estaba activo
    if ($env:VIRTUAL_ENV) {
        Write-Host "Reactivando entorno virtual..."
        & "$venv_path\Scripts\Activate.ps1"
    }
    
    Write-Host "UV instalado y configurado correctamente"
} catch {
    Write-Host "Error al instalar UV: $_"
    Write-Host "Intentando método alternativo..."
    try {
        # Intentar con pipx
        python -m pip install --user pipx
        python -m pipx install uv
        Write-Host "UV instalado correctamente usando pipx"
    } catch {
        Write-Host "Error al instalar UV. Por favor instálalo manualmente:"
        Write-Host "python -m pip install --user uv"
        Write-Host "Y luego agrega el directorio de scripts de Python al PATH"
        exit 1
    }
}

# Configurar CGO_ENABLED
Write-Host "`nConfigurando CGO_ENABLED..."
$env:CGO_ENABLED = "1"
[System.Environment]::SetEnvironmentVariable("CGO_ENABLED", "1", "User")

# Verificar instalaciones
Write-Host "`nVerificando instalaciones..." -ForegroundColor Cyan
Write-Host "Git version: $(git --version)"
Write-Host "Node.js version: $(node --version)"
Write-Host "npm version: $(npm -v)"
Write-Host "Python version: $(python --version)"
Write-Host "Chocolatey version: $(choco --version)"
Write-Host "Go version: $(go version)"
Write-Host "GCC version: $(& "$gccPath\gcc.exe" --version)"
Write-Host "UV version: $(uv --version)"
Write-Host "CGO_ENABLED: $env:CGO_ENABLED"

Write-Host "`nIMPORTANTE: Si ves algún error, por favor:"
Write-Host "1. Cierra esta ventana de PowerShell"
Write-Host "2. Abre una nueva ventana de PowerShell como administrador"
Write-Host "3. Ejecuta el script nuevamente"

# Al final del script, después de todas las instalaciones exitosas
Write-Host "`nActualizando rutas de instalación en default.properties..."

# Obtener rutas usando where
$nodePath = (where.exe node 2>$null)
$goPath = (where.exe go 2>$null)
$chocoPath = (where.exe choco 2>$null)
$nssmPath = (where.exe nssm 2>$null)

# Mantener las rutas existentes de Python y UV
$pythonPath = (Get-Command python).Source
$uvPath = (Get-Command uv).Source

$propertiesToUpdate = @{
    "# Rutas de dependencias instaladas" = ""
    "NODE_PATH" = $nodePath
    "GO_PATH" = $goPath
    "CHOCO_PATH" = $chocoPath
    "PYTHON_PATH" = $pythonPath
    "UV_PATH" = $uvPath
}

# Agregar NSSM solo si se encuentra
if ($nssmPath) {
    $propertiesToUpdate["NSSM_PATH"] = $nssmPath
}

Update-PropertiesFile -filePath "$PSScriptRoot\..\config\default.properties" -properties $propertiesToUpdate

Write-Host "¡Todas las dependencias han sido instaladas y configuradas correctamente!"
Write-Host "Las rutas de instalación han sido actualizadas en config/default.properties"
