const { google } = require('googleapis');
const readline = require('readline');
const fs = require('fs');
const path = require('path');
const http = require('http');

// Función para leer variables de entorno desde .env
function loadEnvVars() {
    
    // Intentar múltiples ubicaciones posibles para el archivo .env
    const possiblePaths = [
        path.join(__dirname, '../config/.env'),
        path.join(process.cwd(), 'config/.env'),
        path.join(process.cwd(), '.env')
    ];
    
    let envPath = null;
    for (const possiblePath of possiblePaths) {
        console.log(`Buscando .env en: ${possiblePath}`);
        if (fs.existsSync(possiblePath)) {
            envPath = possiblePath;
            console.log(`Archivo .env encontrado en: ${envPath}`);
            break;
        }
    }
    
    if (!envPath) {
        console.error('Error: No se encontró el archivo .env en ninguna de las siguientes ubicaciones:');
        possiblePaths.forEach(p => console.error(`- ${p}`));
        console.error('\nPor favor, asegúrate de que el archivo .env existe en una de estas ubicaciones.');
        process.exit(1);
    }
    
    const envVars = {};
    const content = fs.readFileSync(envPath, 'utf8');
    const lines = content.split('\n');
    
    for (const line of lines) {
        const trimmedLine = line.trim();
        if (trimmedLine && !trimmedLine.startsWith('#')) {
            const parts = trimmedLine.split('=');
            if (parts.length === 2) {
                const key = parts[0].trim();
                const value = parts[1].trim().replace(/^["']|["']$/g, '');
                envVars[key] = value;
            }
        }
    }
    
    // Verificar que las variables necesarias estén presentes
    if (!envVars.GOOGLE_CLIENT_ID || !envVars.GOOGLE_CLIENT_SECRET) {
        console.error('Error: Faltan las variables GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET en el archivo .env');
        process.exit(1);
    }
    
    return envVars;
}

// Cargar variables de entorno
const envVars = loadEnvVars();

// Configuración de OAuth2
const oauth2Client = new google.auth.OAuth2(
    envVars.GOOGLE_CLIENT_ID,
    envVars.GOOGLE_CLIENT_SECRET,
    'urn:ietf:wg:oauth:2.0:oob' // Usar el método "out-of-band"
);

// Scopes necesarios para todos los servicios
const SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.modify'
];

// Generar URL de autorización
const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    prompt: 'consent' // Forzar consentimiento para obtener refresh token
});

console.log('Autoriza la aplicación visitando esta URL:');
console.log(authUrl);
console.log('\nDespués de autorizar, copia el código que aparece en la página y pégalo aquí.');

// Crear interfaz de lectura
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

// Solicitar código de autorización
rl.question('Ingresa el código de autorización: ', async (code) => {
    try {
        // Intercambiar código por tokens
        const { tokens } = await oauth2Client.getToken(code);
        
        // Guardar tokens en archivo de configuración
        const configPath = path.join(__dirname, '..', 'config', 'google_auth.json');
        fs.writeFileSync(configPath, JSON.stringify(tokens, null, 2));
        
        // Actualizar el archivo .env con el nuevo refresh token
        const envPath = path.join(__dirname, '..', 'config', '.env');
        let envContent = fs.readFileSync(envPath, 'utf8');
        
        // Buscar y reemplazar el GOOGLE_REFRESH_TOKEN
        const refreshTokenRegex = /^GOOGLE_REFRESH_TOKEN=.*$/m;
        if (refreshTokenRegex.test(envContent)) {
            envContent = envContent.replace(refreshTokenRegex, `GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}`);
        } else {
            // Si no existe, agregarlo al final del archivo
            envContent += `\nGOOGLE_REFRESH_TOKEN=${tokens.refresh_token}`;
        }
        
        fs.writeFileSync(envPath, envContent);
        
        console.log('\n¡Autenticación exitosa!');
        console.log('Tokens guardados en:', configPath);
        console.log('Refresh Token:', tokens.refresh_token);
        console.log('Refresh Token actualizado en el archivo .env');
        
    } catch (error) {
        console.error('\nError al obtener tokens:', error.message);
        console.log('Por favor, intenta nuevamente.');
    } finally {
        rl.close();
    }
}); 