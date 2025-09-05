from typing import Optional
from discord import Client
from discord import Intents
from discord.app_commands import CommandTree

_client: Optional[Client] = None

def init_client() -> Client:
    global _client
    intents = Intents.default()
    intents.message_content = True
    _client = Client(intents=intents)

def get_client():
    return _client

_tree: Optional[CommandTree] = None

def init_command_tree():
    global _tree
    global _client
    _tree = CommandTree(_client)

def get_tree():
    return _tree