# File: /craftNplay/craftNplay/utils/config.py

import os
import json

class Config:
    def __init__(self):
        self.token = os.getenv('DISCORD_BOT_TOKEN')
        self.rcon_password = os.getenv('RCON_PASSWORD')
        self.servers_file = 'servers.json'
        self.default_server = None
        self.load_servers()

    def load_servers(self):
        if not os.path.exists(self.servers_file):
            with open(self.servers_file, 'w') as f:
                json.dump({'servers': {}, 'default_server': None}, f)
        with open(self.servers_file, 'r') as f:
            data = json.load(f)

        # Compatibilidad: si el JSON tiene la clave 'servers', usamos ese formato
        if isinstance(data, dict) and 'servers' in data:
            self.servers = data.get('servers', {}) or {}
            self.default_server = data.get('default_server')
        else:
            # Formato antiguo: todo el dict es la lista de servidores
            self.servers = data or {}
            self.default_server = None

    def save_servers(self):
        data = {
            'servers': self.servers,
            'default_server': self.default_server
        }
        with open(self.servers_file, 'w') as f:
            json.dump(data, f)

    def get_server_info(self, name):
        return self.servers.get(name)

    def add_server(self, name, path, script, rcon_port):
        self.servers[name] = {
            'path': path,
            'script': script,
            'rcon_port': rcon_port
        }
        self.save_servers()

    def set_default_server(self, name: str):
        if name in self.servers:
            self.default_server = name
            self.save_servers()

    def remove_server(self, name):
        if name in self.servers:
            del self.servers[name]
            self.save_servers()

            