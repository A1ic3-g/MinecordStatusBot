# Minecraft Discord Status Bot

A Discord bot that keeps tabs on your Minecraft server and posts updates in a channel. 

## What it does

- Monitors if your server is online or offline
- Shows how many players are connected
- Updates automatically every minute (configurable)
- Stores server settings
- Runs in Docker 

## Quick Start

1. **Set your Discord token:**
   ```bash
   cp .env.example .env
   # Edit .env and add your bot token
   ```

2. **Start it:**
   ```bash
   docker-compose up -d --build
   ```

## Using the Bot

Run `/setup` in a Discord channel with your server details:

```
/setup ip:192.168.1.12 port:25565 interval:30
```


## Running Locally

```bash
uv sync
uv run bot.py
```

## Limitations

Can only track one server. Would be easy to expand to track many servers but I have no need.
