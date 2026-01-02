from discord.ext import commands
import os
import json
import asyncio
import subprocess
from mcrcon import MCRcon

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
                    await ctx.send(f"❌ Error: No se encontró el ejecutable de Playit.gg en la ruta `{PLAYIT_PATH}`.")
                    return False
                await ctx.send("Iniciando el túnel de Playit.gg...")
                self.playit_process = subprocess.Popen(PLAYIT_PATH)
                await asyncio.sleep(5) # Dar tiempo para que se conecte
                await ctx.send("✅ Túnel de Playit.gg iniciado.")
        except Exception as e:
            await ctx.send(f"❌ Error al iniciar Playit.gg: {e}")
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
            await ctx.send(f'❌ Ocurrió un error al iniciar `{server_name}`: {e}')
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
                with MCRcon(rcon_host, self.rcon_password, port=rcon_port) as mcr:
                    mcr.command("stop")
                await ctx.send('Comando "stop" enviado. Esperando 30 segundos...')
                await asyncio.to_thread(process.wait, timeout=30)
                stopped_safely = True
                await ctx.send(f'✅ El servidor `{server_name}` se ha detenido de forma segura.')
            except Exception as e:
                await ctx.send(f'⚠️ No se pudo usar RCON ({e}). Forzando el cierre.')
        
        if not stopped_safely:
            await ctx.send(f'Forzando el cierre del proceso PID: `{process.pid}`...')
            try:
                os.system(f"taskkill /F /T /PID {process.pid}")
                await ctx.send(f'✅ El servidor `{server_name}` ha sido forzado a detenerse.')
            except Exception as e:
                await ctx.send(f'❌ Error al forzar el cierre: {e}')
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
        """Inicia un servidor de Minecraft y Playit.gg."""
        await self._internal_start_server(ctx, server_name)

    @commands.command(name='detener', aliases=['stop'])
    @commands.has_role(ADMIN_ROLE)
    async def detener_command(self, ctx, server_name: str):
        """Detiene un servidor de Minecraft y, si es el último, también Playit.gg."""
        await self._internal_stop_server(ctx, server_name, stop_playit=True)

    @commands.command(name='reiniciar', aliases=['restart'])
    @commands.has_role(ADMIN_ROLE)
    async def reiniciar_command(self, ctx, server_name: str):
        """Reinicia un servidor de Minecraft, pero mantiene Playit.gg activo."""
        await ctx.send(f'🔄 Reiniciando el servidor `{server_name}`...')
        
        # Llama a la lógica interna, PERO no detiene Playit
        if await self._internal_stop_server(ctx, server_name, stop_playit=False):
            await asyncio.sleep(5)  # Esperar un momento
            await self._internal_start_server(ctx, server_name)
    
    # Manejador de errores para este Cog
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            await ctx.send(f"❌ No tienes el rol `{ADMIN_ROLE}` para usar este comando.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ ¡Te falta un argumento! Debes especificar el nombre del servidor. Ejemplo: `!{ctx.command.name} mi_servidor`")
        else:
            await ctx.send(f"Ocurrió un error inesperado en el comando: {error}")

async def setup(bot):
    await bot.add_cog(ServerManagement(bot))