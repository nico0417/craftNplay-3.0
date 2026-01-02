import os
import json
import asyncio
import discord
from discord.ext import commands
from mcstatus import JavaServer
from mcrcon import MCRcon
import socket
import os

# Role requerido para comandos administrativos
ADMIN_ROLE = "Admin"

class ServerStatus(commands.Cog):
    """
    Cog para consultar el estado de los servidores de Minecraft.
    """
    def __init__(self, bot):
        self.bot = bot
        self.rcon_password = os.getenv('RCON_PASSWORD')
        # usar config central
        self.config = getattr(bot, "config_manager", None)

    def load_server_data(self):
        """Carga la base de datos de servidores desde servers.json."""
        if self.config:
            return self.config.servers
        try:
            with open('servers.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @commands.command(name='estado', aliases=['status'])
    async def status_command(self, ctx, server_name: str = None):
        """Consulta el estado de un servidor de Minecraft específico.

        `server_name` es opcional: si no se indica se usa el `default_server` o
        el único servidor registrado.
        """
        # Resolver nombre si es opcional
        if not server_name:
            # Intentar usar config_manager.default_server
            if self.config and getattr(self.config, 'default_server', None):
                server_name = getattr(self.config, 'default_server')
            else:
                servers_tmp = self.load_server_data()
                if not servers_tmp:
                    await ctx.send('❌ No hay servidores registrados.')
                    return
                if len(servers_tmp) == 1:
                    server_name = next(iter(servers_tmp))
                else:
                    await ctx.send('❌ Debes especificar el nombre del servidor.')
                    return

        await ctx.send(f"🔍 Consultando el estado del servidor `{server_name}`...")

        servers_data = self.load_server_data()
        server_info = servers_data.get(server_name)

        if not server_info:
            await ctx.send(f'❌ No se encontró ningún servidor con el nombre `{server_name}` en `servers.json`.')
            return

        # Usar valores por defecto si no están en el JSON
        address = server_info.get('address', 'localhost:25565')
        rcon_port = server_info.get('rcon_port', 25575)
        rcon_host = server_info.get('rcon_host', 'localhost')

        try:
            server = await JavaServer.async_lookup(address)
            status = await server.async_status()
            
            embed = discord.Embed(
                title=f"✅ Servidor `{server_name}` En Línea",
                description=f"El servidor está funcionando correctamente.",
                color=discord.Color.green()
            )
            embed.add_field(name="Versión", value=status.version.name, inline=True)
            embed.add_field(name="Jugadores", value=f"{status.players.online}/{status.players.max}", inline=True)
            embed.add_field(name="Latencia", value=f"{status.latency:.2f} ms", inline=True)
            
            if status.players.online > 0 and self.rcon_password:
                try:
                    def get_player_list():
                        # Comprobar socket primero para detectar fallos de conexión rápidos
                        try:
                            with socket.create_connection((rcon_host, int(rcon_port)), timeout=3):
                                pass
                        except Exception as sock_e:
                            raise RuntimeError(f"Socket error: {sock_e}")

                        with MCRcon(rcon_host, self.rcon_password, port=rcon_port) as mcr:
                            resp = mcr.command("/list")
                            # Lógica mejorada para parsear la respuesta de /list
                            if ":" in resp:
                                parts = resp.split(':', 1)
                                if len(parts) > 1 and parts[1].strip():
                                    player_names = [name.strip() for name in parts[1].split(',')]
                                    return "\n".join(player_names)
                            return None

                    try:
                        player_list = await asyncio.wait_for(asyncio.to_thread(get_player_list), timeout=5)
                    except Exception as rcon_e:
                        raise rcon_e

                    if player_list:
                        embed.add_field(name=f"Jugadores Conectados ({status.players.online})", value=f"```{player_list}```", inline=False)
                    else:
                        embed.add_field(name=f"Jugadores Conectados ({status.players.online})", value="Hay jugadores en el servidor (no se pudo obtener la lista detallada).", inline=False)

                except Exception as rcon_e:
                    embed.add_field(name="Jugadores Conectados", value="No se pudo obtener la lista (error de RCON).", inline=False)
                    embed.set_footer(text=f"Error RCON: {rcon_e}")

            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title=f"❌ Servidor `{server_name}` Fuera de Línea",
                description="No se pudo conectar con el servidor. Puede que esté apagado o iniciándose.",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Error: {e}")
            await ctx.send(embed=embed)

    @status_command.error
    async def status_error(self, ctx, error):
        """Manejo de errores para el comando de estado."""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'❌ ¡Te falta un argumento! Debes especificar el nombre del servidor. Ejemplo: `!{ctx.command.name} mi_servidor`')
        else:
            await ctx.send(f'Ocurrió un error inesperado: {error}')

    @commands.command(name='rcon_test')
    async def rcon_test(self, ctx, server_name: str = None):
        """Prueba rápida de RCON: socket + autenticación.

        `server_name` es opcional y se resuelve usando `default_server` o
        si solo hay un servidor registrado.
        """
        # Resolver server_name igual que en status
        if not server_name:
            if self.config and getattr(self.config, 'default_server', None):
                server_name = getattr(self.config, 'default_server')
            else:
                servers_tmp = self.load_server_data()
                if not servers_tmp:
                    await ctx.send('❌ No hay servidores registrados en `servers.json`.')
                    return
                if len(servers_tmp) == 1:
                    server_name = next(iter(servers_tmp))
                else:
                    await ctx.send('❌ Debes especificar el nombre del servidor. Ejemplo: `!rcon_test mi_servidor`')
                    return

        servers_data = self.load_server_data()
        server_info = servers_data.get(server_name)
        if not server_info:
            await ctx.send(f'❌ No se encontró `{server_name}` en `servers.json`.')
            return

        rcon_host = server_info.get('rcon_host', 'localhost')
        rcon_port = server_info.get('rcon_port', 25575)

        await ctx.send(f'🔎 Probando RCON en `{server_name}` ({rcon_host}:{rcon_port})...')

        # Comprobar socket y autenticación RCON; si falla, intentar leer server.properties
        async def report_props_and_hint(err):
            await ctx.send(f'❌ Prueba RCON fallida: {err}')
            server_path = server_info.get('path')
            if server_path and os.path.isdir(server_path):
                prop_path = os.path.join(server_path, 'server.properties')
                if os.path.exists(prop_path):
                    try:
                        props = {}
                        with open(prop_path, 'r', encoding='utf-8') as pf:
                            for line in pf:
                                line = line.strip()
                                if not line or line.startswith('#') or '=' not in line:
                                    continue
                                k, v = line.split('=', 1)
                                props[k.strip()] = v.strip()

                        enable = props.get('enable-rcon')
                        rpass = props.get('rcon.password')
                        rport = props.get('rcon.port')

                        summary = (
                            'Resumen de `server.properties`:\n'
                            f'- enable-rcon: {enable or "(no encontrado)"}\n'
                            f'- rcon.password: {"(set)" if rpass else "(no establecido)"}\n'
                            f'- rcon.port: {rport or "(no encontrado)"}'
                        )
                        await ctx.send(summary)
                    except Exception as e2:
                        await ctx.send(f'⚠️ Error leyendo `server.properties`: {e2}')
                else:
                    await ctx.send('⚠️ No se encontró `server.properties` en la carpeta del servidor.')
            else:
                await ctx.send('⚠️ No se pudo localizar la carpeta del servidor para leer `server.properties`.')

        try:
            def sock_check():
                s = socket.create_connection((rcon_host, int(rcon_port)), timeout=3)
                s.close()
            await asyncio.wait_for(asyncio.to_thread(sock_check), timeout=4)

            # Comprobar autenticación RCON
            rcon_pass = os.getenv('RCON_PASSWORD')
            if not rcon_pass:
                await ctx.send('⚠️ No hay `RCON_PASSWORD` en las variables de entorno; no se puede probar autenticación.')
                return

            def do_auth():
                with MCRcon(rcon_host, rcon_pass, port=rcon_port) as mcr:
                    return mcr.command('list')

            resp = await asyncio.wait_for(asyncio.to_thread(do_auth), timeout=6)
            await ctx.send('✅ RCON accesible y contraseña válida. Respuesta recibida.')
        except Exception as e:
            await report_props_and_hint(e)

async def setup(bot):
    """Función para cargar el Cog en el bot."""
    await bot.add_cog(ServerStatus(bot))