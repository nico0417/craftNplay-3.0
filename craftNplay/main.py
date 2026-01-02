import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.config import Config

class CraftNPlayBot(commands.Bot):
    """
    Clase principal del bot que hereda de commands.Bot.
    """
    def __init__(self):
        # Definir los intents necesarios para el bot
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # Opcional, pero útil para algunos comandos

        super().__init__(command_prefix='!', intents=intents)

        # Instancia única del manejador de configuración / servers
        self.config_manager = Config()

    async def setup_hook(self):
        """
        Hook que se ejecuta al iniciar el bot para cargar las extensiones (Cogs).
        """
        print("Cargando módulos (Cogs)...")
        # Itera sobre todos los archivos en el directorio 'cogs'
        for filename in os.listdir('./cogs'):
            # Carga el archivo si es un script de Python
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'  -> Módulo {filename} cargado.')
                except Exception as e:
                    print(f'❌ Error al cargar el módulo {filename}: {e}')
        
        print("Todos los módulos han sido procesados.")

    async def on_ready(self):
        """
        Evento que se dispara cuando el bot está conectado y listo.
        """
        print('---')
        print(f'✅ Bot conectado como: {self.user} (ID: {self.user.id})')
        print('---')

async def main():
    """
    Función principal para configurar y ejecutar el bot.
    """
    # Cargar variables de entorno desde el archivo .env
    load_dotenv()
    
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ Error: El token del bot (DISCORD_BOT_TOKEN) no se encontró en las variables de entorno.")
        return

    bot = CraftNPlayBot()
    await bot.start(token)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot desconectado por el usuario.")