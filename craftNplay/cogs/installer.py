import os
import json
from discord.ext import commands
import urllib.request
import urllib.error
import shutil
import time
import subprocess

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
            await ctx.send(f'⚠️ La carpeta `{full_server_path}` ya existe. No se ha realizado ninguna acción.')
            return

        try:
            os.makedirs(full_server_path)
            await ctx.send(f'✅ Carpeta del servidor creada en: `{full_server_path}`')
        except OSError as e:
            await ctx.send(f'❌ Error al crear la carpeta del servidor: {e}')
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

                    # loaders es una lista; elegir el primero (más reciente) o el que tenga campo 'loader'/'version'
                    chosen = None
                    for l in loaders:
                        if isinstance(l, dict) and (l.get('loader') or l.get('version')):
                            chosen = l
                            break
                    if not chosen:
                        chosen = loaders[0]

                    loader_version = chosen.get('loader') or chosen.get('version') or chosen.get('id')
                    if not loader_version:
                        raise RuntimeError('No se pudo determinar la versión del loader de Fabric desde la respuesta de la API')

                    maven_url = f'https://maven.fabricmc.net/net/fabricmc/fabric-installer/{loader_version}/fabric-installer-{loader_version}.jar'
                    installer_path = os.path.join(full_server_path, 'fabric-installer.jar')
                    urllib.request.urlretrieve(maven_url, installer_path)

                    # Ejecutar el instalador en modo servidor y capturar salida
                    await ctx.send('✅ Instalador de Fabric descargado. Ejecutando instalador (puede tardar)...')
                    try:
                        proc = subprocess.run([
                            'java', '-jar', installer_path, 'server', '-mcversion', version, '-downloadMinecraft', '-dir', full_server_path
                        ], check=False, capture_output=True, text=True, timeout=300)

                        # Comprobar si server.jar fue creado
                        created = os.path.exists(os.path.join(full_server_path, 'server.jar'))
                        if created:
                            await ctx.send('✅ Instalación de Fabric completada. `server.jar` generado correctamente.')
                        else:
                            # Informar salida resumida para debug, sin exponer datos sensibles
                            stdout = (proc.stdout or '').strip()[:1000]
                            stderr = (proc.stderr or '').strip()[:1000]
                            await ctx.send('⚠️ El instalador de Fabric terminó pero no generó `server.jar`. Salida del instalador (resumen):')
                            if stdout:
                                await ctx.send(f'```
STDOUT:\n{stdout}
```')
                            if stderr:
                                await ctx.send(f'```
STDERR:\n{stderr}
```')
                            await ctx.send('Por favor revisa manualmente la carpeta o ejecuta el instalador localmente para ver errores completos.')

                    except subprocess.TimeoutExpired:
                        await ctx.send('⚠️ El instalador de Fabric excedió el tiempo de ejecución. Revisa la carpeta manualmente.')
                except Exception as e:
                    await ctx.send(f'⚠️ No se pudo instalar Fabric automáticamente: {e}.')

            else:
                await ctx.send('⚠️ Tipo solicitado no soportado para descarga automática (por ahora). Se creó la estructura; copia el `server.jar` manualmente.')

        except Exception as e:
            await ctx.send(f'⚠️ Error durante la instalación automática: {e}')

        # 7. Intentar arrancar brevemente el servidor para generar world (si hay server.jar)
        server_jar = os.path.join(full_server_path, 'server.jar')
        if os.path.exists(server_jar):
            await ctx.send('⚙️ Iniciando el servidor brevemente para generar archivos (`world`)...')
            try:
                proc = subprocess.Popen(['java', f'-Xms{ram}', f'-Xmx{ram}', '-jar', 'server.jar', 'nogui'], cwd=full_server_path)
                # Esperar un tiempo para que genere archivos
                time.sleep(40)
                # Intentar detenerlo de forma segura enviando stop vía taskkill (no RCON)
                try:
                    proc.kill()
                except Exception:
                    pass
                await ctx.send('✅ Proceso de arranque breve completado. Revisa la carpeta si se creó `world`.')
            except Exception as e:
                await ctx.send(f'⚠️ No se pudo arrancar el servidor automáticamente: {e}')
        else:
            await ctx.send('⚠️ No se encontró `server.jar` en la carpeta; no se puede arrancar automáticamente.')

        await ctx.send('✅ Instalación completada (o creada la estructura). Revisa los pasos manuales si algo falló.')

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