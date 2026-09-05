# Hello Discord bot

This flake packages a Discord bot that responds to `/hello`.

The bot reads its token from the `DISCORD_TOKEN` environment variable. Secret
storage and process supervision are intentionally left to the environment that
runs the package.

```sh
DISCORD_TOKEN=... nix run
```
