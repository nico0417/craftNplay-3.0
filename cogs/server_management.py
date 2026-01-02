from discord.ext import commands
import os
import json
import asyncio
import subprocess
from mcrcon import MCRcon
import socket
from utils.errors import log_exception

# --- CONFIGURACIÓN ---
ADMIN_ROLE = "Admin" 
# Ruta a Playit (deberías moverla a config.py eventualmente)
PLAYIT_PATH = 'C:/Program Files/playit_gg/bin/playit.exe' 

class ServerManagement(commands.Cog):
    """
    Cog para la gestión de los servidores de Minecraft (iniciar, detener, reiniciar).
    """
    def __init__(self, bot):
        self.bot = bot
        self.running_servers = {}
        self.playit_process = None  # Añadimos el tracker para Playit
        self.rcon_password = os.getenv('RCON_PASSWORD')
        self.config = getattr(bot, "config_manager", None)

    def load_server_data(self):
        """Carga la base de datos de servidores desde servers.json."""
        if self.config:
            return self.config.servers
        # Fallback si no hay config manager
        try:
            with open('servers.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def _resolve_server_name(self, ctx, server_name: str):
        """Resuelve el nombre del servidor si es opcional.

        Si se pasa `server_name`, lo devuelve. Si no, y hay un `default_server`
        en el config manager, lo retorna. Si solo hay un servidor registrado,
        lo retorna. En otro caso pide al usuario que especifique el nombre.
        """
        if server_name:
            return server_name

        # Intentar usar config_manager.default_server
        if self.config and getattr(self.config, 'default_server', None):
            default = getattr(self.config, 'default_server')
            if default in self.load_server_data():
                return default

        servers = self.load_server_data()
        if not servers:
            await ctx.send('❌ No hay servidores registrados.')
            return None

        if len(servers) == 1:
            return next(iter(servers))

        await ctx.send('❌ Debes especificar el nombre del servidor.')
        return None

    # --- LÓGICA INTERNA (NO SON COMANDOS) ---

    async def _internal_start_server(self, ctx, server_name: str):
        """Lógica interna para iniciar un servidor."""
        if server_name in self.running_servers and self.running_servers[server_name].poll() is None:
            await ctx.send(f'⚠️ ¡El servidor `{server_name}` ya está en funcionamiento!')
            return False

        servers_data = self.load_server_data()
        server_info = servers_data.get(server_name)

        if not server_info:
            await ctx.send(f'❌ No se encontró ningún servidor con el nombre `{server_name}`.')
            return False

        # --- LÓGICA DE PLAYIT.GG RESTAURADA ---
        try:
            if self.playit_process is None or self.playit_process.poll() is not None:
                if not os.path.exists(PLAYIT_PATH):
                    # Don't leak local paths in public messages; provide actionable hint
                    await ctx.send('❌ Error: No se encontró el ejecutable de Playit.gg en la ruta configurada. Revisa la configuración del bot.')
                    log_exception(FileNotFoundError(PLAYIT_PATH), context='Playit executable missing')
                    return False
                await ctx.send("Iniciando el túnel de Playit.gg...")
                self.playit_process = subprocess.Popen(PLAYIT_PATH)
                await asyncio.sleep(5) # Dar tiempo para que se conecte
                await ctx.send("✅ Túnel de Playit.gg iniciado.")
        except Exception as e:
            log_exception(e, context='Error starting Playit process')
            await ctx.send('❌ Error al iniciar Playit.gg. Revisa los logs del bot.')
            return False
        # --- FIN DE LÓGICA PLAYIT ---

        # --- LÓGICA DEL SERVIDOR DE MINECRAFT ---
        server_path = server_info.get('path')
        script_name = server_info.get('script', 'start.bat')
        script_path = os.path.join(server_path, script_name)

        if not os.path.exists(script_path):
            await ctx.send(f'❌ El script de inicio `{script_path}` no existe.')
            return False

        try:
            await ctx.send(f'✅ Iniciando el servidor `{server_name}`...')
            process = subprocess.Popen(
                script_path,
                cwd=server_path,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            self.running_servers[server_name] = process
            await ctx.send(f'El servidor `{server_name}` se ha iniciado. Dale unos minutos para que esté en línea.')
            return True
        except Exception as e:
            log_exception(e, context=f'Error starting server {server_name}')
            await ctx.send(f'❌ Ocurrió un error al iniciar `{server_name}`. Revisa los logs del bot.')
            return False

    async def _internal_stop_server(self, ctx, server_name: str, stop_playit: bool):
        """Lógica interna para detener un servidor."""
        if server_name not in self.running_servers or self.running_servers[server_name].poll() is not None:
            await ctx.send(f'⚠️ El servidor `{server_name}` no está en funcionamiento.')
            return False

        process = self.running_servers[server_name]
        servers_data = self.load_server_data()
        server_info = servers_data.get(server_name, {})
        
        rcon_port = server_info.get('rcon_port', 25575)
        rcon_host = server_info.get('rcon_host', 'localhost')

        stopped_safely = False
        if self.rcon_password:
            await ctx.send(f'⛔ Intentando un cierre seguro de `{server_name}` vía RCON...')
            try:
                # Comprobar que el puerto está accesible antes de usar MCRcon
                try:
                    with socket.create_connection((rcon_host, int(rcon_port)), timeout=3):
                        pass
                except Exception as sock_e:
                        await ctx.send('⚠️ No se pudo conectar al RCON (socket). Se forzará cierre.')
                        log_exception(sock_e, context=f'RCON socket error for {server_name} at {rcon_host}:{rcon_port}')
                        raise

                def do_rcon_stop():
                    with MCRcon(rcon_host, self.rcon_password, port=rcon_port) as mcr:
                        mcr.command("stop")

                try:
                    await asyncio.wait_for(asyncio.to_thread(do_rcon_stop), timeout=5)
                    await ctx.send('Comando "stop" enviado. Esperando 30 segundos...')
                    await asyncio.to_thread(process.wait, timeout=30)
                    stopped_safely = True
                    await ctx.send(f'✅ El servidor `{server_name}` se ha detenido de forma segura.')
                except asyncio.TimeoutError:
                    await ctx.send('⚠️ Timeout al enviar comando RCON. Forzando cierre.')
                except Exception as rcon_e:
                    log_exception(rcon_e, context=f'RCON command error for {server_name}')
                    await ctx.send('⚠️ Error al usar RCON. Forzando cierre.')
            except Exception:
                # Si cualquier comprobación falla, continuamos con el forzado
                pass
        
        if not stopped_safely:
            await ctx.send(f'Forzando el cierre del proceso PID: `{process.pid}`...')
            try:
                os.system(f"taskkill /F /T /PID {process.pid}")
                await ctx.send(f'✅ El servidor `{server_name}` ha sido forzado a detenerse.')
            except Exception as e:
                    log_exception(e, context=f'Error forcing kill for {server_name}')
                    await ctx.send('❌ Error al forzar el cierre del servidor. Revisa los logs del bot.')
                    return False

        del self.running_servers[server_name]

        # --- LÓGICA DE PLAYIT.GG RESTAURADA ---
        # Si se indica que se detenga, o si ya no quedan servidores corriendo.
        if stop_playit or len(self.running_servers) == 0:
            if self.playit_process and self.playit_process.poll() is None:
                await ctx.send("Cerrando el túnel de Playit.gg...")
                self.playit_process.kill()
                self.playit_process = None
                await ctx.send("Túnel de Playit.gg cerrado.")
        
        return True

    # --- COMANDOS PÚBLICOS DEL BOT ---

    @commands.command(name='iniciar', aliases=['start'])
    @commands.has_role(ADMIN_ROLE)
    async def iniciar_command(self, ctx, server_name: str):
        """Inicia un servidor de Minecraft y Playit.gg.

        `server_name` es obligatorio para `!iniciar`.
        Al iniciarse correctamente, se guarda como `default_server`.
        """
        started = await self._internal_start_server(ctx, server_name)
        if started and self.config and getattr(self.config, 'set_default_server', None):
            try:
                self.config.set_default_server(server_name)
            except Exception:
                # No bloquear si falla el guardado
                pass

    @commands.command(name='detener', aliases=['stop'])
    @commands.has_role(ADMIN_ROLE)
    async def detener_command(self, ctx, server_name: str = None):
        """Detiene un servidor de Minecraft y, si es el último, también Playit.gg.

        `server_name` es opcional: si no se indica se usa el `default_server` o
        el único servidor registrado.
        """
        resolved = await self._resolve_server_name(ctx, server_name)
        if not resolved:
            return
        await self._internal_stop_server(ctx, resolved, stop_playit=True)

    @commands.command(name='reiniciar', aliases=['restart'])
    @commands.has_role(ADMIN_ROLE)
    async def reiniciar_command(self, ctx, server_name: str = None):
        """Reinicia un servidor de Minecraft, pero mantiene Playit.gg activo.

        `server_name` es opcional: si no se indica se usa el `default_server` o
        el único servidor registrado.
        """
        resolved = await self._resolve_server_name(ctx, server_name)
        if not resolved:
            return

        await ctx.send(f'🔄 Reiniciando el servidor `{resolved}`...')
        # Llama a la lógica interna, PERO no detiene Playit
        if await self._internal_stop_server(ctx, resolved, stop_playit=False):
            await asyncio.sleep(5)  # Esperar un momento
            await self._internal_start_server(ctx, resolved)

    @commands.command(name='list')
    async def list_command(self, ctx):
        """Lista los servidores registrados (nombre, versión y tipo). No muestra rutas completas."""
        servers = self.load_server_data()
        if not servers:
            await ctx.send('❌ No hay servidores registrados.')
            return

        rows = []
        for name, info in servers.items():
            version = info.get('version')
            stype = info.get('type')
            path = info.get('path', '')

            # Infer version and type from folder name if not present
            if not version or not stype:
                base = os.path.basename(path) if path else ''
                parts = base.split('_') if base else []
                ver = None
                for p in parts:
                    if p and any(c.isdigit() for c in p) and p.count('.') >= 1:
                        ver = p
                        break
                if not version:
                    version = ver or 'unknown'
                known_types = {'fabric', 'vanilla', 'forge', 'neoforge'}
                t = None
                for p in reversed(parts):
                    lp = p.lower()
                    if lp in known_types:
                        t = lp
                        break
                if not stype:
                    stype = t or (parts[-1].lower() if parts else 'unknown')

            rows.append((name, version, stype))

        # Compute column widths (cap name width)
        name_width = max(len(r[0]) for r in rows + [('Name', '', '')])
        name_width = min(name_width, 30)
        ver_width = max(len(r[1]) for r in rows + [('', 'Version', '')])
        ver_width = min(ver_width, 15)
        type_width = max(len(r[2]) for r in rows + [('', '', 'Type')])
        type_width = min(type_width, 15)

        header = f"{'Name'.ljust(name_width)} | {'Version'.ljust(ver_width)} | {'Type'.ljust(type_width)}"
        sep = '-' * (len(header))
        out_lines = [header, sep]
        for name, version, stype in rows:
            n = (name[:name_width-3] + '...') if len(name) > name_width else name
            out_lines.append(f"{n.ljust(name_width)} | {version.ljust(ver_width)} | {stype.ljust(type_width)}")

        await ctx.send('```\n' + '\n'.join(out_lines) + '\n```')
    
    # Manejador de errores para este Cog
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            await ctx.send(f"❌ No tienes el rol `{ADMIN_ROLE}` para usar este comando.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ ¡Te falta un argumento! Debes especificar el nombre del servidor. Ejemplo: `!{ctx.command.name} mi_servidor`")
        else:
            log_exception(error, context=f'Unhandled error in server_management command: {ctx.command.name if hasattr(ctx, "command") else "?"}')
            await ctx.send('❌ Ocurrió un error inesperado. Se ha registrado en el log del bot.')

async def setup(bot):
    await bot.add_cog(ServerManagement(bot))