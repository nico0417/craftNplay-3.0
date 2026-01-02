import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.config import Config

class CraftNPlayBot(commands.Bot):
    def __init__(self):
        # Intents necesarios
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 

        super().__init__(command_prefix='!', intents=intents)

        self.config_manager = Config()
        self.failed_cogs = [] # Lista de módulos caídos

    async def setup_hook(self):
        """Carga módulos y registra fallos silenciosamente."""
        print("--- Cargando módulos ---")
        
        if not os.path.exists('./cogs'):
            print("❌ Error: No existe la carpeta 'cogs'.")
            return

        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                cog_name = f'cogs.{filename[:-3]}'
                try:
                    await self.load_extension(cog_name)
                    print(f'  ✅ {filename} cargado.')
                except Exception as e:
                    # Registramos el error pero no matamos el bot
                    error_msg = str(e)
                    print(f'  ❌ ERROR EN {filename}: {error_msg}')
                    self.failed_cogs.append((filename, error_msg))

    async def on_ready(self):
        """Reporte de estado al iniciar."""
        print('\n' + '='*40)
        print(f'🤖 Bot conectado: {self.user}')
        
        if self.failed_cogs:
            # 1. REPORTE DETALLADO EN CLI (Solo para ti en la consola)
            print(f"⚠️  ADVERTENCIA: {len(self.failed_cogs)} MÓDULOS FALLARON")
            print('='*40)
            for module, err in self.failed_cogs:
                print(f" - [FALLO] {module}: {err}")
            print('='*40 + '\n')

            # 2. SEÑAL VISUAL EN DISCORD (Estado Rojo)
            await self.change_presence(
                status=discord.Status.dnd, 
                activity=discord.Game(name="⚠️ Error de Sistema")
            )

            # 3. MENSAJE PÚBLICO SIMPLE (En los servidores)
            # Intenta avisar en el canal por defecto de cada servidor
            msg = "⚠️ **Alerta:** El bot se ha iniciado con errores internos. Algunas funciones no estarán disponibles."
            for guild in self.guilds:
                try:
                    # Intenta usar el canal de sistema (bienvenida) o el primer canal de texto disponible
                    channel = guild.system_channel or next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
                    if channel:
                        await channel.send(msg)
                except Exception:
                    pass # Si no tiene permisos, no insistimos.

        else:
            print("✅ Todo funcionando correctamente.")
            print('='*40 + '\n')
            # Estado normal
            await self.change_presence(activity=discord.Game(name="Minecraft Manager"))

async def main():
    load_dotenv()
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("❌ Error: Falta el token en .env")
        return

    bot = CraftNPlayBot()
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass