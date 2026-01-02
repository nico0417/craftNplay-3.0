# CraftNPlay 🚀

CraftNPlay es un bot de Discord escrito en Python para la gestión remota de servidores de Minecraft (Vanilla, NeoForge, Fabric), incluyendo el control integral del túnel de `playit.gg`.

## 🎮 Funcionalidades Principales

* **!iniciar**: Inicia `playit.exe` y el servidor de Minecraft en sus propios procesos.
* **!detener**: Envía un comando `stop` seguro (vía RCON) al servidor y cierra tanto el servidor como `playit.exe`.
* **!reiniciar**: Reinicia el servidor de forma segura sin interrumpir el túnel de `playit.gg`, permitiendo una reconexión rápida.
* **!estado**: Muestra un Embed de Discord con el estado completo del servidor, incluyendo versión, ping y la lista de jugadores conectados (obtenida por RCON para compatibilidad con modo no-premium).

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

---

*Este proyecto fue creado como una herramienta de gestión personal para un servidor de amigos.*
