# Slackbot
This Python script for Slack.

##capabilities
This script can:

*Scan channel and get all it's history.

*Filter channel history with regular expression.

*Save channel history in database with user's reactions on this message.

*Export user's reactions in Google Spreadsheet or in html table.

##Requirements

*For python libraries look into requirements.txt.

*This script require MongoDB instance (it can be set with parameters MONGO_ADDRESS and MONGO_PORT).

*Goggle token can be found here: https://console.developers.google.com/apis/credentials This token is stored in google.json file.

*Slack token can be found here: https://api.slack.com/docs/oauth This token is stored in slack_token filename

##Usage
Running Slackbot.py will parse channel and save emojis in html table "table.html". For other purposes Slackbot.py must be changed
