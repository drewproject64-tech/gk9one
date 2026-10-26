# GK9 Text Tools

Telegram bot: **@GK9Tool_BOT**. A genuine, link-free text utility with exactly three menu buttons.

## What it does
1. **Change Case** — returns UPPERCASE, lowercase, and Title Case versions of submitted text.
2. **Count Words** — counts words, characters (with and without whitespace), and lines.
3. **Clean Text** — removes repeated whitespace and blank lines while keeping nonempty lines.

The bot works entirely within Telegram and uses no external APIs or websites for its text tools.

## Quick start
Requires Python 3.12+.

1. Create the bot at [@BotFather](https://t.me/BotFather), and set its username to **GK9Tool_BOT**.
2. Install dependencies: \`pip install -r requirements.txt\`
3. Set the environment variable \`BOT_TOKEN\` to the bot token from BotFather. Never commit it to GitHub.
4. Start: \`python main.py\`
5. Open https://t.me/GK9Tool_BOT and send \`/start\`.

The first successful launch updates the bot's **name**, **About** (short description), **Description**, and command menu through the official Telegram Bot API. Its username must be set in BotFather (and is verified at startup). A bot profile **photo** must also be set separately using BotFather.

## Commands and behavior
- \`/start\`: welcome screen and the three-button keyboard.
- \`/help\`: tool instructions.
- \`/about\`: profile summary.
- \`/cancel\`: clear the active tool and return to the menu.

Choose one of the three buttons and send a text message. The selected tool keeps working on new messages until you choose another tool or cancel. Input is limited to 1,200 characters per message to keep responses safe for Telegram.

## Deploying on Render
Use **New > Blueprint** with this repository's \`render.yaml\`, which defines a **Python background worker**. Set the \`BOT_TOKEN\` secret when prompted. A background worker is appropriate for long polling and does not need a public port. **Render background workers can require a paid plan**; review costs before creating the service.

Alternatively, create a Background Worker manually:
- Build: \`pip install -r requirements.txt\`
- Start: \`python main.py\`
- Environment: \`BOT_TOKEN=<BotFather token>\`

Only run **one** instance of the bot per token; simultaneous polling instances can conflict. The Dockerfile is an alternate deployment option. Do not set a Telegram webhook for this polling-based bot.

## Testing
Run \`python -m unittest discover -s tests -v\`.

## Security & limitations
- Never put the real token in code, GitHub, or chat.
- No redirects, gambling, payment features, advertising pushes, or forced joins.
- Tool mode is stored in memory, so it resets on process restart. No user text is written to a database.
- Telegram Ads approval is determined by Telegram; functioning code and matched ad text do not guarantee approval.
