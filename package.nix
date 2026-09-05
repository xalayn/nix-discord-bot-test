{ pkgs }:

let
  source = pkgs.lib.fileset.toSource {
    root = ./.;
    fileset = pkgs.lib.fileset.unions [
      ./bot.py
      ./zoho_discord_bot/__init__.py
      ./zoho_discord_bot/__main__.py
      ./zoho_discord_bot/client.py
      ./zoho_discord_bot/config.py
      ./zoho_discord_bot/errors.py
      ./zoho_discord_bot/main.py
      ./zoho_discord_bot/messages.py
      ./zoho_discord_bot/presentation.py
      ./zoho_discord_bot/state.py
      ./zoho_discord_bot/zoho.py
    ];
  };

  python = pkgs.python3.withPackages (pythonPackages: [
    pythonPackages.aiohttp
    (pythonPackages.discordpy.override { withVoice = false; })
  ]);
in
pkgs.writeShellScriptBin "zoho-discord-bot" ''
  exec ${python}/bin/python ${source}/bot.py
''
