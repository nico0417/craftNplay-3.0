# CraftNPlay V3.0 🚀

**CraftNPlay** es un bot de Discord avanzado escrito en Python para la gestión remota y automatizada de servidores de Minecraft (Vanilla, Fabric) en Windows. 

Se especializa en la "Instalación Cero-Toque": descarga, instala, configura la red (RCON) y lanza el servidor con un solo comando de Discord.

## 🌟 Novedades V3.0

* **Instalación Automática Real:** Descarga `server.jar` oficial de Mojang o instaladores de Fabric dinámicamente.
* **Auto-Configuración RCON:** El bot crea el `server.properties` e inyecta la contraseña automáticamente. ¡Adiós al error de conexión!
* **Gestión Inteligente:** Detecta si el servidor se cuelga y fuerza el cierre si RCON no responde.
* **Soporte Playit.gg:** Inicia y cierra el túnel global automáticamente junto con el servidor.

## 🧭 Comandos Principales

### Gestión
* `!iniciar <nombre>`: Enciende el servidor y (opcionalmente) el túnel de Playit.gg.
* `!detener`: Apaga el servidor actual de forma segura (guarda mundo -> stop RCON -> espera). Si falla, fuerza el cierre.
* `!reiniciar`: Reinicia el servidor manteniendo el túnel de Playit activo.
* `!estado`: Muestra RAM, versión, ping y lista de jugadores (con nombres reales vía RCON).
* `!list`: Muestra una tabla con todos los servidores instalados y sus versiones.

### Instalación y Diagnóstico
* `!install <tipo> <version> <nombre>`: 
    * Crea la carpeta y descarga el servidor.
    * Acepta EULA automáticamente.
    * **Activa RCON y configura puertos.**
    * Ejemplo: `!install vanilla 1.21.1 survival` o `!install fabric 1.20.1 mods`.
* `!rcon_test`: Diagnóstico técnico. Prueba la conexión TCP y autenticación RCON para detectar problemas de red.

## 🛠️ Guía de Instalación Rápida

1.  **Descargar el Proyecto:**
    ```bash
    git clone [https://github.com/nico0417/craftNplay-3.0.git](https://github.com/nico0417/craftNplay-3.0.git)
    cd craftNplay-3.0
    ```

2.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuración de Entorno (.env):**
    Crea un archivo `.env` en la misma carpeta que `main.py` con tus secretos:
    ```env
    DISCORD_BOT_TOKEN=Tu_Token_De_Discord_Aqui
    RCON_PASSWORD=UnaContrasenaSeguraParaTusServers
    ```

4.  **Ejecutar:**
    ```bash
    python main.py
    ```

## 📂 Estructura de Archivos (Automática)

El bot organizará tus servidores automáticamente (por defecto en `C:\Servidores_Minecraft` o lo que configures).

* `servers.json`: Base de datos local (se gestiona sola, no tocar).
* `bot_errors.log`: Registro de errores técnicos para depuración.

---
*Este proyecto fue creado como una herramienta de gestión personal para un servidor de amigos.*