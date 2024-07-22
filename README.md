# SRSInfo-Discord-Bot
Discord bot to message a channel when a new stream on SRS video server starts using http-callbacks. 

## Install:
1. http-callbacks should be routed to ip:3000/stream or you can direct them to /on_publish and /on_unpublish. See SRS http-callbacks how to set up your SRS config.
2. Clone repo and edit the settings.json. You need to enter the bot TOKEN to have the bot work. URL_HOST and URL_EXT are recommened to set to have working links to the stream. The rest of the settings are if you want to mannally preset them or set them later with slash commands
3. Use docker to create container
4. Invite bot using scopes bot and application.commands. In bot permissions allow sending messages and read message history.
4. Use /setchannel comannd in the channel you want the bot to send stream messages in.

## Docker:
```
clone git https://github.com/DudeShift/SRSInfo-Discord-Bot
docker build -t srsinfo-bot .
```
```
docker run -d \
    -v $(pwd)/settings.json:/app/settings.json \
    -p 3000:3000 \
    --name srsinfo-bot \
    --restart unless-stopped \
    srsinfo-bot
```

## Commands:
| Command               | Description                                 |
|-----------------------|---------------------------------------------|
| `/ping`               | Sends the bot's latency                    |
| `/togglebot`          | Toggles enable/disable stream messages      |
| `/setchannel`         | Sets the bot to the channel where the command was sent |
| `/filter add`         | Adds a stream name to the filter list       |
| `/filter remove`      | Removes a stream name from the filter list  |
| `/filter set`         | Sets the filter type (open, whitelist, blacklist) |
| `/filter view`        | Views the current filter list               |

## settings.json
Note: In the docker run command, the settings.json is mounted inside the container. That means any edits from the container are reflected on the settings.json outside of the container. This is used easily copying current filter list that other users may have changed before a update (ie: if you had to remove and recreate the container)

| Name                 | Type    | Default         | Description |
|----------------------|---------|-----------------|-------------|
| TOKEN                | String  | "YourTokenHere" | Replace null with your token string            |
| CHANNEL_ID           | Integer | null            |  Set default channel_id (right-click channel in discord)           |
| URL_DOMAIN             | String  | null            | The ip or domain of the SRS server or where your streams are coming from |
| URL_EXT               | String | null            | The file extension of the stream if needed (ie, ".flv" for http-flv) 
| DELETE_ON_UNPUBLISHED| Boolean | true            |  Delete stream messages on stream ending (for false still WIP)           |
| ENABLE_STREAM_MESSAGES | Boolean | true            | Allow the bot to send messages about a new stream            |
| ENABLE_DEBUG         | Boolean | false           | Show custom debug messages in docker log            |
| FILTER_OPTION        | String  | "open"          | Set filter type "whitelist", "blacklist", or "open" for all streams            |
| FILTER_LIST          | Array   | []              | List of stream names ('stream' from SRS) used for filtering            |









