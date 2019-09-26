# The Spread Bot
A Telegram Bot for The Spread with order and payment capabilities for customers of The Spread.

## Usage
- `/menu` to check the menu.
- `/order` to place your order.
- `/cart` to check your cart.
- `/offers` to view available deals.
- `/pay` to proceed to payment.
- `/cancel` to cancel your order.
- `/terms` to read our Terms & Conditions.

Several hidden administrative commands with restricted access are also available to provide easy management, servicing and maintenance.

## Setup

**Heroku App Config Vars:**

``` json
  [
  {
    "key": "ADMIN_LIST",
    "value": "[<user-id-1>, <user-id-2>, ...]"
  },
  {
    "key": "BOT_TOKEN",
    "value": "<id>:<token>"
  },
  {
    "key": "DATABASE_URL",
    "value": "postgres://<user>:<password>@<server>:<port>/<database>"
  },
  {
    "key": "SUPER_ADMIN",
    "value": "[<user-id-1>, <user-id-2>, ...]"
  },
  {
    "key": "TZ",
    "value": "Asia/Singapore"
  },
  {
    "key": "WEBHOOK_URL",
    "value": "https://<app-name>.herokuapp.com/"
  }
  ]
```

Finally, issue an HTTPS request to `https://api.telegram.org/bot<id>:<token>/setWebhook?url=https://<app-name>.herokuapp.com/<id>:<token>` to enable the webhook for the bot.

Other notes:
- Normal port for PostGreSQL is `5432`.
- Initial data was manually converted from SQLite database to Heroku Postgres using the [ESF Database Migration Toolkit](https://www.dbsofts.com/) with the corresponding temporary database credentials provided by Heroku.

## TODO

- Neaten the source code file structure (separate functions by purpose/type as different modules).

## Additional Resources

- More about The Spread: https://www.facebook.com/thespread.sg/
