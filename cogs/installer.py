import os
import json
from discord.ext import commands
import urllib.request
import urllib.error
import shutil
import time
import subprocess
import asyncio

class Installer(commands.Cog):
    """
    Cog para instalar y registrar nuevos servidores de Minecraft.
    """
    def __init__(self, bot):
        self.bot = bot
        # Usar el manager central que está en el bot
        self.config = bot.config_manager 
        # Ruta por defecto donde crear servidores si no se indica
        self.default_parent = os.environ.get('CNP_DEFAULT_SERVERS_PATH', r'C:/Documents/servers')

    @commands.command(name='install')
    @commands.is_owner()
    async def install_server(self, ctx, server_type: str, version: str, base_name: str, parent_path: str = None):
        """
        Crea la estructura de carpetas, EULA y config. de RAM para un nuevo servidor.
        Uso: !install <tipo> <version> <nombre> <ruta_padre>
        Ejemplo: !install neoforge 1.21.1 mi_servidor D:\\ServidoresMC
        """
        # 1. Determinar y validar la ruta padre
        if not parent_path:
            parent_path = self.default_parent

        if not os.path.isdir(parent_path):
            try:
                os.makedirs(parent_path, exist_ok=True)
            except OSError as e:
                await ctx.send(f'❌ La ruta padre `{parent_path}` no existe y no se pudo crear: {e}')
                return

        # 2. Crear la ruta completa y la carpeta del servidor
        folder_name = f"{base_name}_{version}_{server_type}"
        full_server_path = os.path.join(parent_path, folder_name)

        if os.path.exists(full_server_path):
            # CAMBIO: Solo mostramos folder_name
            await ctx.send(f'⚠️ La carpeta `{folder_name}` ya existe. No se ha realizado ninguna acción.')
            return

        try:
            os.makedirs(full_server_path)
            # CAMBIO: Mensaje más corto y seguro
            await ctx.send(f'✅ Carpeta del servidor creada: `{folder_name}`')
        except OSError as e:
            await ctx.send(f'❌ Error al crear la carpeta: {e}')
            return

        # 3. Crear y aceptar el EULA automáticamente
        try:
            eula_path = os.path.join(full_server_path, 'eula.txt')
            with open(eula_path, 'w') as f:
                f.write('eula=true\n')
            await ctx.send('✅ `eula.txt` creado y aceptado.')
        except Exception as e:
            await ctx.send(f'❌ Error al crear `eula.txt`: {e}')
            return # Detener si esto falla

        # 4. Crear el archivo de argumentos de RAM (para Fabric/NeoForge/Forge)
        # Estimación de RAM por tipo
        if server_type.lower() == 'vanilla':
            ram = '4G'
        else:
            ram = '6G'

        jvm_args_content = (
            "# Configuración de JVM generada por CraftNPlay\n"
            "# -Xms: RAM inicial asignada\n"
            "# -Xmx: RAM máxima asignada\n"
            f"-Xms{ram}\n"
            f"-Xmx{ram}\n"
        )
        try:
            jvm_args_path = os.path.join(full_server_path, 'user_jvm_args.txt')
            with open(jvm_args_path, 'w') as f:
                f.write(jvm_args_content)
            await ctx.send('✅ `user_jvm_args.txt` creado con 6GB de RAM por defecto.')
        except Exception as e:
            await ctx.send(f'❌ Error al crear `user_jvm_args.txt`: {e}')
        # 4.5 Crear server.properties con RCON ACTIVADO automáticamente
        # Esto evita que tengas que editarlo a mano después de instalar.
        rcon_pass = os.getenv('RCON_PASSWORD', 'password_seguro_por_defecto')
        
        properties_content = (
            "# Archivo generado por CraftNPlay\n"
            "enable-rcon=true\n"
            "rcon.port=25575\n"
            f"rcon.password={rcon_pass}\n"
            "server-port=25565\n"
            f"motd=Servidor {base_name} - CraftNPlay\n"
            "difficulty=normal\n"
        )
        
        try:
            prop_path = os.path.join(full_server_path, 'server.properties')
            # Solo lo creamos si no existe para no sobrescribir configs de un server existente
            if not os.path.exists(prop_path):
                with open(prop_path, 'w') as f:
                    f.write(properties_content)
                await ctx.send('✅ `server.properties` creado con **RCON habilitado**.')
            else:
                await ctx.send('ℹ️ `server.properties` ya existía, no se modificó (asegúrate de activar RCON manual).')
        except Exception as e:
            await ctx.send(f'⚠️ No se pudo crear server.properties: {e}')

        # 4.6 Crear el script de inicio (run.bat)
        # Usamos los argumentos definidos en user_jvm_args.txt para mantenerlo limpio
        run_bat_content = (
            "@echo off\n"
            "title CraftNPlay Server Console\n"
            "java @user_jvm_args.txt -jar server.jar nogui\n"
        )
        
        try:
            bat_path = os.path.join(full_server_path, 'run.bat')
            with open(bat_path, 'w') as f:
                f.write(run_bat_content)
            await ctx.send('✅ `run.bat` creado correctamente.')
        except Exception as e:
            await ctx.send(f'⚠️ Error al crear `run.bat`: {e}')
        
        # 5. Registrar el nuevo servidor usando el método del config manager
        if base_name in self.config.servers:
            await ctx.send(f'⚠️ Ya existe una configuración para un servidor llamado `{base_name}`. Se sobrescribirá.')
        
        self.config.add_server(
            name=base_name,
            path=full_server_path,
            script="run.bat", # Asumimos que el instalador creará "run.bat"
            rcon_port=25575 # Puerto RCON por defecto
        )
        await ctx.send(f'💾 ¡Servidor `{base_name}` registrado! Ahora puedes usar `!iniciar {base_name}`.')

        # 6. Intentar descargar e instalar automáticamente según tipo
        await ctx.send('⬇️ Intentando descargar e instalar automáticamente los archivos del servidor...')

        try:
            if server_type.lower() == 'vanilla':
                # Descargar server.jar oficial de Mojang usando launchermeta
                await ctx.send('🔎 Descargando server.jar oficial (Mojang) para la versión solicitada...')
                try:
                    manifest_url = 'https://launchermeta.mojang.com/mc/game/version_manifest.json'
                    with urllib.request.urlopen(manifest_url, timeout=10) as mf:
                        manifest = json.load(mf)

                    vinfo = next((v for v in manifest.get('versions', []) if v.get('id') == version), None)
                    if not vinfo:
                        raise RuntimeError('Versión no encontrada en el manifest oficial de Mojang')

                    with urllib.request.urlopen(vinfo.get('url'), timeout=10) as vf:
                        vjson = json.load(vf)

                    server_download = vjson.get('downloads', {}).get('server', {})
                    server_url = server_download.get('url')
                    if not server_url:
                        raise RuntimeError('No se encontró server.jar para esa versión (descarga no disponible)')

                    dest_jar = os.path.join(full_server_path, 'server.jar')
                    urllib.request.urlretrieve(server_url, dest_jar)
                    await ctx.send('✅ server.jar (Vanilla) descargado correctamente.')
                except Exception as e:
                    await ctx.send(f'⚠️ No se pudo descargar el server.jar oficial automáticamente: {e}. Deberás mover manualmente el `server.jar` a la carpeta del servidor.')

            elif server_type.lower() == 'fabric':
                # Intentar descargar el instalador de Fabric y ejecutarlo
                await ctx.send('🔎 Intentando instalar Fabric para la versión solicitada...')
                try:
                    # Preferir el endpoint específico por versión
                    loaders_url = f'https://meta.fabricmc.net/v2/versions/loader/{version}'
                    try:
                        with urllib.request.urlopen(loaders_url, timeout=10) as r:
                            loaders = json.load(r)
                    except Exception:
                        # Fallback al endpoint general
                        with urllib.request.urlopen('https://meta.fabricmc.net/v2/versions/loader', timeout=10) as r:
                            loaders = json.load(r)

                    if not loaders:
                        raise RuntimeError('No se encontró un loader de Fabric para esa versión.')

                    # Helper de debug: registrar en archivo y enviar resumen a canal (recortado)
                    debug_log_path = os.path.join(full_server_path, 'install_debug.log')
                    def log_debug(msg):
                        ts = time.strftime('%Y-%m-%d %H:%M:%S')
                        entry = f'[{ts}] {msg}\n'
                        try:
                            with open(debug_log_path, 'a', encoding='utf-8') as df:
                                df.write(entry)
                        except Exception:
                            pass

                    async def send_debug_line(line):
                        try:
                            # Evitar mensajes excesivamente largos
                            if len(line) > 1900:
                                line = line[:1900] + '... (truncated)'
                            await ctx.send(f'`[install-debug]` {line}')
                        except Exception:
                            pass

                    log_debug(f'Starting Fabric install debug for mc_version={version}.')

                    # Comprobar que `java` esté disponible antes de ejecutar instaladores
                    try:
                        java_check = subprocess.run(['java', '-version'], capture_output=True, text=True, timeout=5)
                        if java_check.returncode != 0:
                            await ctx.send('⚠️ `java` no parece estar disponible o devuelve error. Instalación de Fabric necesita Java para ejecutar el instalador. Instala Java y vuelve a intentarlo.')
                            log_debug('Java check failed: non-zero returncode')
                            return
                    except Exception:
                        await ctx.send('⚠️ `java` no se encontró en el sistema. Instalación de Fabric requiere Java. Por favor instala Java en el host antes de usar esta función.')
                        log_debug('Java not found in PATH')
                        return

                    # Normalizador de versiones
                    def _normalize_loader_version(v):
                        # Handle common shapes returned by Fabric meta endpoints.
                        if isinstance(v, str):
                            return v
                        if isinstance(v, dict):
                            # Prefer nested 'loader' object -> 'version'
                            loader_obj = v.get('loader')
                            if isinstance(loader_obj, dict):
                                ver = loader_obj.get('version')
                                if isinstance(ver, str):
                                    return ver
                                maven = loader_obj.get('maven')
                                if isinstance(maven, str):
                                    parts = maven.split(':')
                                    if parts:
                                        return parts[-1]

                            # Older/alternate shapes: top-level 'version' or 'maven' keys
                            if 'version' in v and isinstance(v['version'], str):
                                return v['version']
                            if 'maven' in v and isinstance(v['maven'], str):
                                parts = v['maven'].split(':')
                                if parts:
                                    return parts[-1]
                            if 'id' in v and isinstance(v['id'], str):
                                return v['id']
                            # As a last resort, try 'name'
                            if 'name' in v and isinstance(v['name'], str):
                                return v['name']
                            # If still unknown, return a compact string to avoid embedding full JSON
                            try:
                                return json.dumps(v, separators=(',', ':'), ensure_ascii=False)
                            except Exception:
                                return str(v)
                        return str(v)

                    # Priorizar combos conocidos (Option A)
                    priority_combos = {
                        # mc_version: list of (loader_version, installer_version) tuples
                        '1.21.11': [('0.18.4', '1.1.0')],
                    }

                    # Función de descarga con comprobación previa (HEAD-like) y traza
                    def try_download_stream(url, dest_path):
                        log_debug(f'Trying download URL: {url}')
                        req = urllib.request.Request(url, headers={'User-Agent': 'CraftNPlay/Installer'})
                        try:
                            with urllib.request.urlopen(req, timeout=15) as resp:
                                code = getattr(resp, 'status', None) or getattr(resp, 'getcode', lambda: None)()
                                headers = resp.headers if hasattr(resp, 'headers') else {}
                                content_length = headers.get('Content-Length') or headers.get('content-length')
                                log_debug(f'HTTP {code} for {url}; Content-Length={content_length}')
                                if code and int(code) == 200:
                                    # Stream to file
                                    with open(dest_path, 'wb') as out_f:
                                        shutil.copyfileobj(resp, out_f)
                                    size = os.path.getsize(dest_path)
                                    log_debug(f'Downloaded {size} bytes to {dest_path}')
                                    return True, code, content_length
                                else:
                                    return False, code, content_length
                        except urllib.error.HTTPError as he:
                            log_debug(f'HTTPError {he.code} for {url}: {he}')
                            return False, getattr(he, 'code', None), None
                        except Exception as e:
                            log_debug(f'Error downloading {url}: {e}')
                            return False, None, None

                    downloaded = False
                    candidates = loaders if isinstance(loaders, list) else [loaders]

                    # Build a map of loader_version -> installer_versions for candidates that actually match the requested mc version
                    loader_map = {}
                    for cand in candidates:
                        loader_version = _normalize_loader_version(cand)
                        loader_details = None
                        # Try mc-specific endpoint first; if it fails (400), try loader-only endpoint
                        urls_to_try = [
                            f'https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_version}',
                            f'https://meta.fabricmc.net/v2/versions/loader/{loader_version}',
                        ]
                        for loader_detail_url in urls_to_try:
                            try:
                                log_debug(f'Fetching loader details from {loader_detail_url}')
                                req = urllib.request.Request(loader_detail_url, headers={'User-Agent': 'CraftNPlay/Installer'})
                                with urllib.request.urlopen(req, timeout=10) as rd:
                                    loader_details = json.load(rd)
                                    log_debug(f'Fetched loader details from {loader_detail_url} (len={len(str(loader_details))})')
                                    break
                            except urllib.error.HTTPError as he:
                                log_debug(f'HTTPError {he.code} for {loader_detail_url}: {he}')
                                # If 400, continue to next url; otherwise also continue but log
                                continue
                            except Exception as e:
                                log_debug(f'Could not fetch loader details for {loader_version} from {loader_detail_url}: {e}')
                                continue

                        installer_versions = []
                        if isinstance(loader_details, list) and loader_details:
                            for it in loader_details:
                                if isinstance(it, dict) and it.get('version'):
                                    installer_versions.append(it.get('version'))
                                elif isinstance(it, str):
                                    installer_versions.append(it)
                        if installer_versions:
                            loader_map[loader_version] = installer_versions
                            log_debug(f'Loader {loader_version} has installers: {installer_versions}')

                    # First, try explicit priority combos if the mc version matches
                    if version in priority_combos:
                        for loader_v, inst_v in priority_combos[version]:
                            direct_url = f'https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_v}/{inst_v}/server/jar'
                            dest_jar = os.path.join(full_server_path, 'server.jar')
                            ok, code, clen = try_download_stream(direct_url, dest_jar)
                            await send_debug_line(f'Tried priority URL {direct_url} -> HTTP {code} Content-Length={clen}')
                            if ok and os.path.exists(dest_jar):
                                await ctx.send(f'✅ Fabric server.jar descargado desde URL prioritaria (loader={loader_v}, installer={inst_v}).')
                                downloaded = True
                                break

                    # If we have loader_map entries, try direct endpoints for those loaders only
                    if not downloaded and loader_map:
                        for loader_version, installer_versions in loader_map.items():
                            for inst_ver in installer_versions:
                                direct_url = f'https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_version}/{inst_ver}/server/jar'
                                dest_jar = os.path.join(full_server_path, 'server.jar')
                                ok, code, clen = try_download_stream(direct_url, dest_jar)
                                await send_debug_line(f'Tried {direct_url} -> HTTP {code} Content-Length={clen}')
                                if ok and os.path.exists(dest_jar):
                                    await ctx.send(f'✅ Fabric server.jar descargado directamente (loader={loader_version}, installer={inst_ver}).')
                                    downloaded = True
                                    break
                            if downloaded:
                                break

                    # Fallback: only try installer JARs for loaders that matched (loader_map)
                    if not downloaded and loader_map:
                        for loader_version in loader_map.keys():
                            try:
                                maven_url = f'https://maven.fabricmc.net/net/fabricmc/fabric-installer/{loader_version}/fabric-installer-{loader_version}.jar'
                                installer_path = os.path.join(full_server_path, f'fabric-installer-{loader_version}.jar')
                                ok, code, clen = try_download_stream(maven_url, installer_path)
                                await send_debug_line(f'Tried maven {maven_url} -> HTTP {code} Content-Length={clen}')
                                if not ok or not os.path.exists(installer_path):
                                    log_debug(f'Installer JAR not available at {maven_url} (loader={loader_version})')
                                    continue
                                await ctx.send(f'✅ Instalador de Fabric descargado (loader={loader_version}). Ejecutando instalador (puede tardar)...')
                                proc = subprocess.run([
                                    'java', '-jar', installer_path, 'server', '-mcversion', version, '-downloadMinecraft', '-dir', full_server_path
                                ], check=False, capture_output=True, text=True, timeout=300)
                                created = os.path.exists(os.path.join(full_server_path, 'server.jar'))
                                stdout = (proc.stdout or '').strip()[:4000]
                                stderr = (proc.stderr or '').strip()[:4000]
                                log_debug(f'Installer stdout: {stdout[:1000]}')
                                log_debug(f'Installer stderr: {stderr[:1000]}')
                                if created:
                                    await ctx.send(f'✅ Instalación de Fabric completada (loader={loader_version}). `server.jar` generado correctamente.')
                                    downloaded = True
                                    break
                                else:
                                    await ctx.send('⚠️ El instalador de Fabric terminó pero no generó `server.jar`. Resumen de salida:')
                                    if stdout:
                                        await ctx.send(f'```STDOUT:\n{stdout}```')
                                    if stderr:
                                        await ctx.send(f'```STDERR:\n{stderr}```')
                            except Exception as e:
                                log_debug(f'Error running installer for loader={loader_version}: {e}')
                                continue
                    if not downloaded:
                        await ctx.send('⚠️ No se pudo obtener `server.jar` automáticamente para Fabric con los loaders disponibles. Revisa `install_debug.log` en la carpeta del servidor.')
                except Exception as e:
                    await ctx.send(f'⚠️ No se pudo instalar Fabric automáticamente: {e}.')

            else:
                await ctx.send('⚠️ Tipo solicitado no soportado para descarga automática (por ahora). Se creó la estructura; copia el `server.jar` manualmente.')

        except Exception as e:
            await ctx.send(f'⚠️ Error durante la instalación automática: {e}')

        # 7. Intentar arrancar brevemente el servidor para generar world (si hay server.jar)
        server_jar = os.path.join(full_server_path, 'server.jar')
        if os.path.exists(server_jar):
            await ctx.send('⚙️ Iniciando el servidor brevemente para generar archivos (`world`)... (El bot esperará 60s)')
            try:
                # Usamos CREATE_NEW_CONSOLE para que sea un proceso independiente
                proc = subprocess.Popen(
                    ['java', f'-Xms{ram}', f'-Xmx{ram}', '-jar', 'server.jar', 'nogui'],
                    cwd=full_server_path,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                
                # Esperamos de forma asíncrona (el bot sigue vivo para otros comandos)
                await asyncio.sleep(60) 

                # CIERRE ROBUSTO Y SILENCIOSO
                # 1. Intentamos matar el objeto proceso de Python
                if proc.poll() is None: # Solo si sigue corriendo
                    proc.kill()
                    try:
                        proc.wait(timeout=5) # Esperar a que muera para evitar zombies
                    except subprocess.TimeoutExpired:
                        pass

                # 2. Aseguramos limpieza con taskkill (Solo si sigue vivo)
                # Usamos subprocess.run en vez de os.system para redirigir la salida a la basura
                # y evitar mensajes de error rojos en tu consola.
                if proc.poll() is None:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL, # Silenciar éxito
                        stderr=subprocess.DEVNULL  # Silenciar error "no running instance"
                    )
                
                await ctx.send('✅ Proceso de arranque breve completado. Revisa la carpeta si se creó `world`.')
            except Exception as e:
                await ctx.send(f'⚠️ No se pudo arrancar el servidor automáticamente: {e}')
        else:
            await ctx.send('⚠️ No se encontró `server.jar` en la carpeta; no se puede arrancar automáticamente.')

        await ctx.send('✅ Instalación completada. Usa `!iniciar` para encenderlo definitivamente.')

    @install_server.error
    async def install_error(self, ctx, error):
        """Manejo de errores para el comando de instalación."""
        if isinstance(error, commands.NotOwner):
            await ctx.send('❌ Este comando solo puede ser usado por el dueño del bot.')
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'❌ Faltan argumentos. Uso correcto: `!install <tipo> <version> <nombre> <ruta_padre>`')
        else:
            await ctx.send(f'Ocurrió un error inesperado: {error}')

async def setup(bot):
    """Función para cargar el Cog en el bot."""
    await bot.add_cog(Installer(bot))