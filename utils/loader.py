import importlib
from pathlib import Path
from .discord import get_tree

def load_modules_from_directory(directory_path):
    """
    Dynamically load all Python modules from a directory and execute setup functions.
    """
    directory = Path(directory_path)
    if not directory.exists():
        return

    for file_path in directory.glob('*.py'):
        if file_path.name.startswith('_'):
            continue

        module_name = f"{directory.name}.{file_path.stem}"

        try:
            importlib.import_module(module_name)
            print(f"Loaded {module_name}")
        except Exception as e:
            print(f"Failed to load {module_name}: {e}")

async def sync_commands():
    try:
        synced = await get_tree().sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

def auto_load_commands():
    load_modules_from_directory('commands')

def auto_load_events():
    load_modules_from_directory('events')
