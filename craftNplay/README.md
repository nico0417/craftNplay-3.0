# CraftNPlay 🚀

CraftNPlay es un bot de Discord escrito en Python para la gestión remota de servidores de Minecraft (Vanilla, NeoForge, Fabric), incluyendo el control integral del túnel de `playit.gg`.

## 🎮 Funcionalidades Principales

* **!iniciar**: Inicia `playit.exe` y el servidor de Minecraft en sus propios procesos.
* **!detener**: Envía un comando `stop` seguro (vía RCON) al servidor y cierra tanto el servidor como `playit.exe`.
* **!reiniciar**: Reinicia el servidor de forma segura sin interrumpir el túnel de `playit.gg`, permitiendo una reconexión rápida.
* **!estado**: Muestra un Embed de Discord con el estado completo del servidor, incluyendo versión, ping y la lista de jugadores conectados (obtenida por RCON para compatibilidad con modo no-premium).

## 🧭 Comandos principales

- `!iniciar <nombre>`: Inicia `playit.exe` (si está configurado) y el servidor de Minecraft. Al iniciar correctamente, el servidor se guarda como `default_server` para comandos posteriores.
- `!detener [nombre]`: Detiene el servidor indicado; si se omite `nombre` y sólo hay un servidor registrado o hay un `default_server`, se usará ese. Intenta un cierre seguro por RCON, y si falla, fuerza el cierre.
- `!reiniciar [nombre]`: Reinicia el servidor indicado (o el `default_server` si no se pasa nombre).
- `!estado [nombre]` / `!status [nombre]`: Consulta el estado de un servidor (usa `default_server` si se omite el nombre cuando procede).
- `!rcon_test [nombre]`: Prueba conexión y autenticación RCON; si falla, muestra un resumen de las claves relevantes en `server.properties` (sin exponer rutas locales).
- `!list`: Lista los servidores registrados en columnas alineadas: `Name | Version | Type`.
- `!install <tipo> <version> <nombre> [ruta_padre]`: Crea la carpeta del servidor y, cuando es posible, descarga/instala los artefactos automáticamente (`vanilla`, `fabric` con limitaciones). Ver notas abajo.

* **!rcon_test**: Comando de depuración que prueba conexión y autenticación RCON. Si falla, muestra un resumen de los ajustes relevantes en `server.properties` (`enable-rcon`, `rcon.password`, `rcon.port`) sin exponer rutas del sistema.
* **!install**: Instala automáticamente un servidor en una carpeta nueva. Soporta descarga automática para Paper (opción `vanilla`) y un instalador básico de Fabric. Crea `eula.txt`, `user_jvm_args.txt` y `run.bat`. Puede arrancar el servidor por un breve periodo (30-60s) para generar el `world`.

## 🛠️ Instalación y Configuración

1.  **Clonar el Repositorio:**
    ```sh
    git clone [https://github.com/nico0417/craftNplay.git](https://github.com/nico0417/craftNplay.git)
    cd craftNplay
    ```

2.  **Instalar Dependencias:**
    ```sh
    pip install -r requirements.txt
    ```

3.  **Configurar el Servidor de Minecraft:**
    * Asegúrate de tener un servidor de Minecraft en su propia carpeta.
    * En el archivo `server.properties` del servidor, habilita RCON (necesario para los comandos `!detener` y `!estado`):
        ```properties
        enable-rcon=true
        rcon.port=25575
        rcon.password=TuContraseñaSeguraRCON
        ```

4.  **Configurar las Variables de Entorno:**
    El bot carga las credenciales de forma segura. Debes configurar las siguientes variables de entorno en tu sistema:
    * `DISCORD_BOT_TOKEN`: El token secreto de tu bot de Discord.
    * `RCON_PASSWORD`: La contraseña que acabas de poner en `server.properties`.

5.  **Actualizar las Rutas:**
    * Dentro de `bot.py`, ajusta las siguientes variables en la sección de configuración para que coincidan con tus rutas locales:
        ```python
        BASE_PATH = 'C:/Ruta/A/Tu/Servidor'
        SCRIPT_PATH = os.path.join(BASE_PATH, 'iniciar_servidor.bat')
        SERVER_DIRECTORY = BASE_PATH
        PLAYIT_PATH = 'C:/Program Files/playit_gg/bin/playit.exe'
        ```

6.  **Ejecutar el Bot:**
    ```sh
    python bot.py
    ```

## 📦 Comando `!install` (nuevo)

Uso básico:

 - `!install vanilla 1.21.1 nombre_server`  → descarga Vanilla para 1.21.1 y configura el servidor.
 - `!install fabric 1.19.2 nombre_server`   → descarga Fabric y configura el servidor.

Qué hace:

 - Crea la carpeta del servidor en la ruta indicada (por defecto `C:/Documents/servers` si no se especifica).
 - Descarga los archivos necesarios (cuando estén disponibles automáticamente).
 - Crea `eula.txt` (aceptando), `user_jvm_args.txt`, `server.properties` (con `enable-rcon=false` por seguridad) y `run.bat` con la configuración de RAM apropiada.
 - Registra el servidor en `servers.json` para que puedas usar `!iniciar`/`!detener`/`!estado`.
 - Opcionalmente arranca el servidor por 30–60s para que genere `world` y archivos iniciales.

Limitaciones y notas sobre instalador automático

- `vanilla`: descarga el `server.jar` oficial desde los manifiestos de Mojang y suele funcionar automáticamente.
- `fabric`: el instalador intenta varios flujos (descarga directa del server.jar desde meta.fabricmc, o descarga y ejecución de `fabric-installer.jar`). En algunos combos de versión/loader/installer la generación automática puede fallar; en ese caso revisa `install_debug.log` dentro de la carpeta del servidor y ejecuta el instalador manualmente.
- Si la automatización falla, el comando deja la estructura creada y deberás copiar manualmente el `server.jar` en la carpeta del servidor.

Notas de seguridad:

 - El bot nunca expone rutas completas del sistema en mensajes públicos; solo muestra estados y recomendaciones.
 - Para RCON, configura `rcon.password` en `server.properties` y establece `RCON_PASSWORD` en las variables de entorno del sistema.

## ✅ Recomendaciones y buenas prácticas

- Seguridad RCON: usa una contraseña fuerte y no la compartas. Evita exponer el puerto RCON públicamente; usa firewall y redes internas cuando sea posible.
- Backups: realiza copias periódicas de la carpeta `world` y de `server.properties` antes de ejecutar instalaciones automáticas.
- Java: instala una versión de Java compatible con la versión de Minecraft objetivo (Java 17+ para 1.18+ en la mayoría de casos). Verifica `java -version` en el host.
- Entorno del bot: configura variables de entorno seguras (por ejemplo con un servicio de systemd, Windows Task Scheduler o contenedor) en vez de ponerlas en texto plano.
- Logs: revisa el archivo `bot_errors.log` en la raíz del proyecto para trazas completas de errores; el bot envía mensajes concisos en Discord.
- Registro de servidores: `servers.json` contiene la estructura usada por el bot. Formato actual:

```json
{
    "servers": {
        "mi_servidor": {
            "path": "C:/.../mi_servidor_1.21.11_fabric",
            "script": "run.bat",
            "rcon_port": 25575,
            "type": "fabric",
            "version": "1.21.11"
        }
    },
    "default_server": "mi_servidor"
}
```

El bot hace escrituras atómicas en `servers.json` y si el fichero se detecta corrupto lo renombra a `servers.json.corrupt` y recrea uno limpio.
- Actualizaciones: guarda una copia de `servers.json` antes de grandes cambios; la carga automática hace backup en `servers.json.corrupt` si el fichero está corrupto.


---

*Este proyecto fue creado como una herramienta de gestión personal para un servidor de amigos.*
