{ pkgs }:

let
  python = pkgs.python3.withPackages (pythonPackages: [
    (pythonPackages.discordpy.override { withVoice = false; })
  ]);
in
pkgs.writeShellScriptBin "hello-discord-bot" ''
  exec ${python}/bin/python ${./bot.py}
''
