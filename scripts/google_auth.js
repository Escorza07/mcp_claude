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
        
        console.log('\n¡Autenticación exitosa!');
        console.log('Tokens guardados en:', configPath);
        console.log('Refresh Token:', tokens.refresh_token);
        
        // Actualizar repositories.json con el nuevo token
        const reposPath = path.join(__dirname, '..', 'config', 'repositories.json');
        const repos = JSON.parse(fs.readFileSync(reposPath, 'utf8'));
        
        // Actualizar tokens en todos los MCPs de Google
        repos.repositories.forEach(repo => {
            if (repo.name.includes('google') || repo.name.includes('gmail')) {
                if (repo.env_vars) {
                    repo.env_vars.GOOGLE_REFRESH_TOKEN = tokens.refresh_token;
                }
            }
        });
        
        fs.writeFileSync(reposPath, JSON.stringify(repos, null, 2));
        console.log('repositories.json actualizado con el nuevo token');
        
    } catch (error) {
        console.error('\nError al obtener tokens:', error.message);
        console.log('Por favor, intenta nuevamente.');
    } finally {
        rl.close();
    }
}); 