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
        # Ensure file exists with a sane default
        if not os.path.exists(self.servers_file):
            try:
                with open(self.servers_file, 'w', encoding='utf-8') as f:
                    json.dump({'servers': {}, 'default_server': None}, f)
            except Exception:
                # If we cannot create the file, keep in-memory defaults
                self.servers = {}
                self.default_server = None
                return

        # Load and validate JSON safely
        try:
            with open(self.servers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            # Corrupt or unreadable JSON: back it up and start fresh
            try:
                bad_path = self.servers_file + '.corrupt'
                os.replace(self.servers_file, bad_path)
            except Exception:
                pass
            self.servers = {}
            self.default_server = None
            # attempt to recreate a fresh file
            try:
                with open(self.servers_file, 'w', encoding='utf-8') as f:
                    json.dump({'servers': {}, 'default_server': None}, f)
            except Exception:
                pass
            return

        # Compatibilidad: si el JSON tiene la clave 'servers', usamos ese formato
        if isinstance(data, dict) and 'servers' in data:
            self.servers = data.get('servers', {}) or {}
            self.default_server = data.get('default_server')
        else:
            # Formato antiguo: todo el dict es la lista de servidores
            if isinstance(data, dict):
                self.servers = data or {}
            else:
                self.servers = {}
            self.default_server = None

    def save_servers(self):
        data = {
            'servers': self.servers,
            'default_server': self.default_server
        }
        # Write atomically to avoid corruption
        tmp_path = self.servers_file + '.tmp'
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp_path, self.servers_file)
        except Exception:
            # Best-effort fallback
            try:
                with open(self.servers_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
            except Exception:
                pass

    def get_server_info(self, name):
        return self.servers.get(name)

    def list_servers(self):
        """Return a shallow copy of registered servers."""
        return dict(self.servers)

    def get_default_server(self):
        return self.default_server

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

            