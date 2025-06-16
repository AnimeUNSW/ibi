# Ibi!

## Requirements
- Python 3.12+
- uv
- Discord token
- PostgreSQL database URI
- Mailersend API key
- JWT secret key
- A Discord server with stuff in it
## Setup
```sh
uv sync
```
👍. Also fill out `src/bot/.env`.
## Usage
```sh
uv run bot
```
This will automatically start the bot and the server. Note that in production it is recommended to use at least CPython's first level of optimisation by running
```sh
uv run python -O src/bot
```
