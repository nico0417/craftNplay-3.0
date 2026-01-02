import os
import json
from discord.ext import commands

class Installer(commands.Cog):
    """
    Cog para instalar y registrar nuevos servidores de Minecraft.
    """
    def __init__(self, bot):
        self.bot = bot
        # Usar el manager central que está en el bot
        self.config = bot.config_manager 

    @commands.command(name='install')
    @commands.is_owner()
    async def install_server(self, ctx, server_type: str, version: str, base_name: str, *, parent_path: str):
        """
        Crea la estructura de carpetas, EULA y config. de RAM para un nuevo servidor.
        Uso: !install <tipo> <version> <nombre> <ruta_padre>
        Ejemplo: !install neoforge 1.21.1 mi_servidor D:\\ServidoresMC
        """
        # 1. Validar que la ruta padre exista
        if not os.path.isdir(parent_path):
            await ctx.send(f'❌ La ruta padre `{parent_path}` no existe o no es un directorio.')
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
        jvm_args_content = (
            "# Configuración de JVM generada por CraftNPlay\n"
            "# -Xms: RAM inicial asignada\n"
            "# -Xmx: RAM máxima asignada\n"
            "-Xms6G\n"
            "-Xmx6G\n"
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
        
        # 6. Actualizar el mensaje de "Próximos pasos"
        await ctx.send(f'**Próximos pasos (manuales):**\n'
                       f'1. Descarga el instalador de `{server_type}` (versión `{version}`).\n'
                       f'2. **MUÉVELO** a la nueva carpeta (`{full_server_path}`).\n'
                       f'3. **EJECÚTALO** allí para que instale los archivos del servidor. Esto creará el `run.bat` automáticamente.')

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