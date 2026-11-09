# GK9 Telegram Bot

GK9 (@GK9Tool_BOT) offers two publicly accessible sections: **Text Tools** and **Games & Links**, which contains links to external gaming websites.

Both sections remain available regardless of the administrator's preferred /start section. Every /start shows the featured content and an explicit menu for both sections.

## Public commands

- /start: Show the featured section, then both available choices.
- /tools: Change Case, Count Words, and Clean Text. Input limit: 1,200 characters.
- /games: Open the SYARIKAT MY image, caption, and four external site buttons.
- /help, /about, /cancel: User assistance and tool selection.

## Admin controls

Set **ADMIN_ID** in Render to the administrator's numeric Telegram user ID. No admin access is granted if it is missing.

- /admin: Show REDIRECT, REVERSE, and Check Status buttons.
- /redirect or REDIRECT: Feature Games & Links first for future /start requests.
- /reverse or REVERSE: Feature Text Tools first for future /start requests.

This setting **does not hide or disable either section**, and switching modes **does not broadcast messages** to existing users.

The preference is stored in SQLite at **GK9_MODE_DB_PATH**, default data/gk9_mode.sqlite3. For persistence across Render redeployments, use a persistent disk and set GK9_MODE_DB_PATH to a path on it (for example, /var/data/gk9_mode.sqlite3). Without a persistent disk, mode may reset to Text Tools after redeployment.

## Deploy and test

This is a Python 3.12 aiogram 3.x polling bot configured as a Render background worker.

1. Add BOT_TOKEN and ADMIN_ID as secret environment variables on Render.
2. Optional: configure GK9_MODE_DB_PATH for persistent storage.
3. Redeploy the latest GitHub commit.
4. Run unit tests: python -m unittest discover -s tests -v

The code deliberately does not update the bot's **name**, **username**, **About**, **short description**, or **description** in Telegram. Existing welcome image and four direct website URL buttons are preserved.

Bot content and any Telegram ad copy must disclose both features, including external gaming links. Switching the featured section does not make gambling ads eligible for Telegram Ads; never use the switch to hide ad destinations during review.
