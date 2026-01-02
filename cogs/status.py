import os
import json
import asyncio
import discord
from discord.ext import commands
from mcstatus import JavaServer
from mcrcon import MCRcon

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
    async def status_command(self, ctx, server_name: str):
        """Consulta el estado de un servidor de Minecraft específico."""
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
                        with MCRcon(rcon_host, self.rcon_password, port=rcon_port) as mcr:
                            resp = mcr.command("/list")
                            # Lógica mejorada para parsear la respuesta de /list
                            if ":" in resp:
                                parts = resp.split(':', 1)
                                if len(parts) > 1 and parts[1].strip():
                                    player_names = [name.strip() for name in parts[1].split(',')]
                                    return "\n".join(player_names)
                            return None

                    player_list = await asyncio.to_thread(get_player_list)

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

async def setup(bot):
    """Función para cargar el Cog en el bot."""
    await bot.add_cog(ServerStatus(bot))