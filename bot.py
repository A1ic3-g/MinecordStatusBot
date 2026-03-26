import discord
from discord.ext import tasks, commands
from discord import app_commands
from mcstatus import JavaServer
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG_FILE = "data/config.json"
CONFIG_DIR = "data"

# Default values
DEFAULT_UPDATE_INTERVAL = 60
DEFAULT_MINECRAFT_PORT = 25565

# Config keys
CONFIG_GUILD_ID = "guild_id"
CONFIG_CHANNEL_ID = "channel_id"
CONFIG_MESSAGE_ID = "message_id"
CONFIG_SERVER_IP = "server_ip"
CONFIG_SERVER_PORT = "server_port"
CONFIG_INTERVAL = "interval"

# Ensure data directory exists
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

def load_config(config_file: str) -> dict:
    """Load configuration from JSON file."""
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return json.load(f)
    return {}

def save_config(config: dict, config_file: str) -> None:
    """Save configuration to JSON file."""
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)

class DiscordStatusBot(commands.Bot):
    """Discord bot that monitors Minecraft server status"""
    def __init__(self, config_file: str = CONFIG_FILE):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(intents=intents)
        self.config_file = config_file
        self.config: dict = load_config(config_file)

    async def setup_hook(self):
        await self.tree.sync()
        interval = self.config.get(CONFIG_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        self.update_status.change_interval(seconds=interval)
        self.update_status.start()

    async def _check_server_status(self, ip: str, port: int) -> tuple[bool, int, int]:
        """Check if Minecraft server is online and get player counts."""
        try:
            server = JavaServer.lookup(f"{ip}:{port}")
            status = await server.async_status()
            return True, status.players.online, status.players.max
        except Exception:
            return False, 0, 0

    def _create_status_embed(self, online: bool, players: int, max_players: int) -> discord.Embed:
        """Create a status embed for the Minecraft server."""
        embed = discord.Embed(
            title="Minecraft Server Status",
            color=discord.Color.green() if online else discord.Color.red()
        )
        embed.add_field(name="Status", value="Online" if online else "Offline", inline=True)
        if online:
            embed.add_field(name="Players", value=f"{players}/{max_players}", inline=True)
        embed.timestamp = discord.utils.utcnow()
        return embed

    async def _get_message_from_config(self) -> discord.Message | None:
        """Fetch the status message from stored config."""
        channel_id = self.config.get(CONFIG_CHANNEL_ID)
        message_id = self.config.get(CONFIG_MESSAGE_ID)

        if not all([channel_id, message_id]):
            return None

        try:
            channel = self.get_channel(channel_id)
            if not channel:
                channel = await self.fetch_channel(channel_id)

            if not channel:
                logger.error(f"Channel {channel_id} not found.")
                return None

            return await channel.fetch_message(message_id)
        except Exception as e:
            logger.error(f"Error fetching message: {e}")
            return None

    @tasks.loop(seconds=60)
    async def update_status(self):
        """Periodically update the server status message."""
        if not self.config:
            return

        try:
            server_ip = self.config.get(CONFIG_SERVER_IP)
            server_port = self.config.get(CONFIG_SERVER_PORT, DEFAULT_MINECRAFT_PORT)

            if not server_ip:
                return

            online, players, max_players = await self._check_server_status(server_ip, server_port)
            embed = self._create_status_embed(online, players, max_players)
            message = await self._get_message_from_config()

            if message:
                await message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Error updating status: {e}")

    @update_status.before_loop
    async def before_update_status(self):
        await self.wait_until_ready()

    @app_commands.command(name="setup", description="Configure the Minecraft server monitoring")
    @app_commands.describe(
        ip="Minecraft server IP",
        port=f"Minecraft server port (default: {DEFAULT_MINECRAFT_PORT})",
        interval=f"Update interval in seconds (default: {DEFAULT_UPDATE_INTERVAL})"
    )
    async def setup(self, interaction: discord.Interaction, ip: str, port: int = DEFAULT_MINECRAFT_PORT, interval: int = DEFAULT_UPDATE_INTERVAL):
        """Setup the Minecraft server monitoring for a channel."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return

        await interaction.response.defer()

        # Check server availability
        online, players, max_players = await self._check_server_status(ip, port)
        embed = self._create_status_embed(online, players, max_players)

        # Send initial status message
        message = await interaction.channel.send(embed=embed)

        # Update configuration
        self._save_setup_config(interaction, ip, port, interval, message.id)

        # Update the loop interval
        self.update_status.change_interval(seconds=interval)

        await interaction.followup.send(
            f"Status monitoring setup successfully for `{ip}:{port}`. Updates every {interval} seconds.",
            ephemeral=True
        )

    def _save_setup_config(self, interaction: discord.Interaction, ip: str, port: int, interval: int, message_id: int) -> None:
        """Save the setup configuration to file."""
        self.config[CONFIG_GUILD_ID] = interaction.guild_id
        self.config[CONFIG_CHANNEL_ID] = interaction.channel_id
        self.config[CONFIG_MESSAGE_ID] = message_id
        self.config[CONFIG_SERVER_IP] = ip
        self.config[CONFIG_SERVER_PORT] = port
        self.config[CONFIG_INTERVAL] = interval
        save_config(self.config, self.config_file)
        logger.info(f"Setup configured for {ip}:{port} with {interval}s update interval")

if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_TOKEN environment variable not set.")
    else:
        logger.info("Starting Discord bot...")
        bot = DiscordStatusBot(CONFIG_FILE)
        bot.run(TOKEN)
