# File: /craftNplay/craftNplay/utils/config.py

import os
import json

class Config:
    def __init__(self):
        self.token = os.getenv('DISCORD_BOT_TOKEN')
        self.rcon_password = os.getenv('RCON_PASSWORD')
        self.servers_file = 'servers.json'
        self.load_servers()

    def load_servers(self):
        if not os.path.exists(self.servers_file):
            with open(self.servers_file, 'w') as f:
                json.dump({}, f)
        with open(self.servers_file, 'r') as f:
            self.servers = json.load(f)

    def save_servers(self):
        with open(self.servers_file, 'w') as f:
            json.dump(self.servers, f)

    def get_server_info(self, name):
        return self.servers.get(name)

    def add_server(self, name, path, script, rcon_port):
        self.servers[name] = {
            'path': path,
            'script': script,
            'rcon_port': rcon_port
        }
        self.save_servers()

    def remove_server(self, name):
        if name in self.servers:
            del self.servers[name]
            self.save_servers()

            