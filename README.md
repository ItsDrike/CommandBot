# Deprecation Message

This repository is now deprecated, but the bot development isn't stopped completely. There is a completely new version of this bot, with a whole new codebase and much better code: visit https://github.com/Codin-Nerds/Neutron-Bot for the continued version

# Former Readme

[![Discord](https://img.shields.io/static/v1?label=ItsDrike&logo=discord&message=Join&color=%237289DA&logoColor=white)](https://discord.gg/ZVyn3fk)
[![Build Status](https://travis-ci.com/ItsDrike/CommandBot.svg?branch=master)](https://travis-ci.com/ItsDrike/CommandBot)


## About the bot

CommandBot can manage most of your administrative tasks on your server
It includes features like:

* Kicks, Bans, Tempbans, Mutes
* It will keep track of all given infractions for every user
* Detailed logging to see what's going on in your server
* Show you information about any player/member or the server itself
* Clean messages from channels (You can clean specific user, or even regex pattern)
* Fun commands

Using the bot is very simple, to show list of the commands, use **!help**

## Installation

If you want to try and run this bot on your own, follow this guide:

### Creating the bot on Discord

1. Create bot on Discord's [bot portal](https://discord.com/developers/applications/)
2. Make a **New Application**
3. Go to **Bot** settings and click on **Add Bot**
4. Give **Administrator** permission to bot
5. You will find your bot **TOKEN** there, it is important that you save it
6. Go to **OAuth2** and click bot, than add **Administrator** permissions
7. You can follow the link that will appear to add the bot to your discord server

### Running bot

1. Clone the repository (or fork it if you want to make changes)
2. Install **pipenv** `pip install pipenv`
3. Build the virtual enviroment from Pipfile.lock `pipenv sync`
4. Create **.env** file with `BOT_TOKEN="[Your bot token]"`
5. Configure the settings (More about this in **Settings** section)
6. Run the virtual enviroment `pipenv shell`
7. Use `python -m bot` to run the bot (You have to be in CommandBot/ directory)

### Using Systemd

There is an option to use systemd on Linux to run this bot using the **commandbot.service** file. This can be good to restart on unexpected crashes, automatic starting on boot of your machine and running in the background.

Note that you need to [**Install Linux Screen**](https://linuxize.com/post/how-to-use-linux-screen/) so that you can access the output at any time.\
(If you don't want this, you can adjust the **commandbot.service** to fit your needs)

1. Create a symbolic link to the **commandbot.service** in **/etc/systemd/system** `sudo ln -s [absolute path to commandbot.service] /etc/systemd/system/commandbot.service`
2. Reload the daemon `sudo systemctl daemon-reload`
3. \[OPTIONAL\] Start the bot on boot `sudo systemctl enable commandbot.service`
4. Start the bot service `sudo systemctl start commandbot.service`
5. If you need to check the output, you can use `sudo screen -R CommandBot` (`Ctrl-A-D` to detach)

## Bot Configuration

The bot has a default configuration file **default_config.yaml** but this config applies for our server, in order to get this to work on your server, you need to create **config.yaml** file, and add all the config you want to change. (The rest will be taken from default config, no need to retype it.)

### Settings which needs to be be changed

It is advised to look at the whole default config and adjust everything you need in the **config.yaml** file, but the minimum you need to change is this:

* Guild
  * ID (ID of your server)
  * Channels configuration (IDs of channels)
  * Roles configuration (IDs of your roles)

### Settings which are recommended to change / take a look at

* Bot
  * Prefix (Default command prefix is '!')
* Details
  * Rules (All of the rules in your server)
* Filter (domain and word watchlist)
* Style (Change all of the emojis the bot is using)
