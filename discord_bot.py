import discord
import json
import logging
import asyncio
from flask import Flask, request, Response
from threading import Thread
from datetime import datetime

# Global dictionary to store message ID
message_references = {}

# Load settings from the JSON file
def load_settings():
    with open('/app/settings.json', 'r') as f:
        return json.load(f)

def save_settings(settings):
    with open('/app/settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

settings = load_settings()
TOKEN = settings['TOKEN']
CHANNEL_ID = settings['CHANNEL_ID']
URL_DOMAIN = settings['URL_DOMAIN']
URL_EXT = settings['URL_EXT']
DELETE_ON_UNPUBLISHED = settings['DELETE_ON_UNPUBLISHED']
ENABLE_STREAM_MESSAGES = settings['ENABLE_STREAM_MESSAGES']
ENABLE_DEBUG = settings['ENABLE_DEBUG']
FILTER_OPTION = settings['FILTER_OPTION']
FILTER_LIST = settings['FILTER_LIST']

app = Flask(__name__)

# Configure logging
log_level = logging.DEBUG if ENABLE_DEBUG else logging.INFO

# Create and configure custom logger
custom_logger = logging.getLogger('custom')
custom_logger.setLevel(log_level)
custom_handler = logging.StreamHandler()
custom_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
custom_logger.addHandler(custom_handler)

# Configure discord and werkzeug loggers
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.INFO)  # Set to INFO to ignore DEBUG messages

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)  # Set to INFO to ignore DEBUG messages

# Create a logger for the bot
logger = custom_logger  # Use the custom logger for bot logging

# Setup Flask logger
flask_logger = custom_logger  # Use the custom logger for Flask


intents = discord.Intents.default()  # Create the default intents
bot = discord.Bot(intents=intents)  # Use Bot instead of Client for slash commands

bot_ready = asyncio.Event()  # Event to indicate the bot is ready

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}')
    bot_ready.set()  # Signal that the bot is ready

### Route POST based on url to handle SRS HTTP-Callbacks     
@app.route('/<action>', methods=['POST'])
def handle_http_callback(action):
    if action not in ['stream', 'on_publish', 'on_unpublish']:
        return Response('Invalid callback action', status=400)
    
    data = request.json

    # Ensure the bot is ready before using asyncio
    if not bot_ready.is_set():
        logger.debug("Bot was NOT ready to receive")
    else:
        asyncio.run_coroutine_threadsafe(parse_json_event(data), bot.loop)
    
    # Respond with HTTP 200 and a plain integer value of 0
    return Response('0', status=200)

### Read json event 
async def parse_json_event(eventData):
    # Check if Channel ID is set first
    if CHANNEL_ID is None:
        logger.debug("No channel ID is set in settings or slash command")
        return None
    
    action = eventData.get('action')
    stream = eventData.get('stream')
    param  = eventData.get('param')
    streamURL = URL_DOMAIN + eventData.get('stream_url') + URL_EXT
    logger.debug(action + ", " + stream + ", " + param + ", " + streamURL)
    
    match FILTER_OPTION:
        case "whitelist":
            if stream not in FILTER_LIST:
                logger.debug(stream + " is not whitelisted")
                return
        case "blacklist":
            if stream in FILTER_LIST:
                logger.debug(stream + " is blacklisted")
                return
        case "open":
            pass
        case _:
            logger.debug("Error: Unknown filter option")
            return
    if not ENABLE_STREAM_MESSAGES:
        logger.debug("Stream Messages are disabled")
        return     
    match action:
        case "on_publish":
            embed = discord.Embed(
                title="\U0001F4FA " + stream + " is live",
                color=discord.Color.blurple(),
            )
            embed.add_field(name=streamURL, value="") 
              
            # Save the message ID to update later
            if stream in message_references:
                logger.debug("Another on_publish for " + stream)
                try:
                    original_message = await channel.fetch_message(message_references[stream])
                    await original_message.delete()
                except discord.NotFound:
                        logger.debug("Message not found.")
                except discord.HTTPException as e:
                        logger.debug(f"HTTP error: {e}")
            message = await send_to_channel(embed)
            message_references[stream] = message.id
            

        case "on_unpublish":
            message_id = message_references.pop(stream, None)
            if message_id:
                channel = bot.get_channel(CHANNEL_ID)
                if channel:
                    try:
                        original_message = await channel.fetch_message(message_id)
                        if DELETE_ON_UNPUBLISHED:
                            await original_message.delete()
                        else: 
                            updated_embed = discord.Embed(
                                title="\U0001F534 " + stream + " Offline",
                                description="Stream Ended",
                                color=discord.Color.red()
                            )
                            await original_message.edit(embed=updated_embed)
                    except discord.NotFound:
                        logger.debug("Message not found.")
                    except discord.HTTPException as e:
                        logger.debug(f"HTTP error: {e}")
                else:
                    logger.debug("Channel not found.")
            else:
                logger.debug("No previous embed found to update.")
        case _:
            logger.debug("Unsupported http-callback action, see github repo")
    logger.debug("Active Streams: " + ", ".join(message_references))

async def send_to_channel(embed):
    if CHANNEL_ID is None:
        logger.debug("No channel ID is set in settings or slash command")
        return None
    
    channel = bot.get_channel(CHANNEL_ID)  # Ensure this is an integer
    if channel:
        if isinstance(embed, discord.Embed):  # Check if the argument is an Embed object
            try:
                message = await channel.send(embed=embed)
                return message # Return the message object
            except discord.Forbidden:
                logger.debug("Permission error: The bot does not have permission to send messages to this channel.")
            except discord.HTTPException as e:
                logger.debug(f"HTTP error: {e}")
        else:
            logger.debug("The argument is not an Embed object.")
    else:
        logger.debug("Channel not found")
    return None


####################
### BOT COMMANDS ###
####################
@bot.command(name="ping", description="Sends the bot's latency")
async def ping(ctx):
    embed = discord.Embed (
            title = "\U0001F44B " + f"Pong! Latency is {bot.latency}",
            color = discord.Color.blurple()
    )
    await ctx.respond(embed=embed, ephemeral=True)

@bot.command(name="togglebot", description="Toggles enable/disable stream messages")
async def toggle_bot(ctx):
    global ENABLE_STREAM_MESSAGES
    ENABLE_STREAM_MESSAGES = not ENABLE_STREAM_MESSAGES
    status = "\U00002705 Enabled" if ENABLE_STREAM_MESSAGES else "\U0000274C Disabled"
    embed = discord.Embed (
            title = f"{status} stream messages",
            color = discord.Color.blurple()
    )
    await ctx.respond(embed=embed, ephemeral=True)

@bot.command(name="setchannel", description="Set the bot to the channel to where command was sent from")
async def set_channel(ctx):
    channel_id = ctx.channel.id  # Get the ID of the channel where the command was sent
    
    # Update settings with the new channel ID
    settings['CHANNEL_ID'] = channel_id
    save_settings(settings)
    
    # Update the CHANNEL_ID variable with the new value
    global CHANNEL_ID
    CHANNEL_ID = channel_id

    embed = discord.Embed (
            title = "\U00002705 " + f"Set bot to channel_id: `{channel_id}`",
            color = discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

### Subgroup commands for managing the filter list from discord
manage_filterlist = bot.create_group("filter", "Manage the Filter List")

@manage_filterlist.command(name="add", description="Add stream name to filter list")
async def add(ctx, stream: discord.Option(str)):
    if stream in FILTER_LIST:
        embed = discord.Embed (
            title = "\U0000274C " + f"{stream} already in filter list",
            color = discord.Color.gold()
        )
    elif stream:
        FILTER_LIST.append(stream)
        settings['FILTER_LIST'] = FILTER_LIST
        save_settings(settings)
        embed = discord.Embed (
            title = "\U00002705 " + f"Added `{stream}` to the filter list.",
            color = discord.Color.green()
        )
    else:
        embed = discord.Embed (
            title = "\U0001F914 Please provide a stream name to add.",
            color = discord.Color.gold()
        )
    await ctx.respond(embed=embed, ephemeral=True)

### Autocomplete
# Autocomplete function for FILTER_LIST
async def get_filter_list_suggestions(ctx: discord.AutocompleteContext):
    # Provide autocomplete suggestions based on entries in FILTER_LIST.
    return [item for item in FILTER_LIST if item.startswith(ctx.value.lower())]

@manage_filterlist.command(name="remove", description="Remove stream name to filter list")
async def remove(ctx: discord.ApplicationContext, stream: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_filter_list_suggestions))):
    if stream:
        if stream in FILTER_LIST:
            FILTER_LIST.remove(stream)
            settings['FILTER_LIST'] = FILTER_LIST
            save_settings(settings)
            embed = discord.Embed (
                title = "\U00002705 " + f"Removed `{stream}` from the filter list.",
                color = discord.Color.green()
            )
        else:
            embed = discord.Embed (
                title = "\U0000274C " + f"`{stream}` is not in the filter list.",
                color = discord.Color.gold()
            )
    else:
        embed = discord.Embed (
            title = "\U0001F914 Please provide a stream name to remove.",
            color = discord.Color.gold()
        )
    await ctx.respond(embed=embed, ephemeral=True)

@manage_filterlist.command(name="set", description="Set the filter type")
async def set(ctx: discord.ApplicationContext, option: discord.Option(str, choices=['open', 'whitelist', 'blacklist'])):
    valid_filters = ["whitelist", "blacklist", "open"]
    if option in valid_filters:
        settings['FILTER_OPTION'] = option
        save_settings(settings)
        global FILTER_OPTION
        FILTER_OPTION = option
        embed = discord.Embed (
            title = "\U00002705 " + f"Set filter to `{option}`",
            color = discord.Color.green()
        )
    else:
        embed = discord.Embed (
            title = "\U0001F914 Please provide a valid filter type (whitelist, blacklist, open).",
            description = f"Current filter type is `{FILTER_OPTION}`",
            color = discord.Color.gold()
        )
    await ctx.respond(embed=embed, ephemeral=True)

@manage_filterlist.command(name="view", description="View the filter list")
async def view(ctx):
    filterlist_message = "\n".join(FILTER_LIST)
    embed = discord.Embed (
            title = f"\U0001F4C4 Filter List | `{FILTER_OPTION}`",
            description = f"```\n{filterlist_message}\n```",
            color = discord.Color.light_grey()
        )
    await ctx.respond(embed=embed, ephemeral=True)

############
### MAIN ###
############

if __name__ == '__main__':
    # Run the Flask app to handle HTTP callbacks
    def run_flask():
        app.run(host="0.0.0.0", port=3000)

    # Run Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Run the Discord bot
    bot.run(TOKEN)
