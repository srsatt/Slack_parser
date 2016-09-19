# Slackbot

##Основные возможности

*Сканирование истории канала и сохранение ее в БД.

*Экспорт лайков у каждого задания в Google Spreadsheet или же в отдельные словарь.

##Установка

pyenv

*Для работы необходима база данных MongoDB с двумя таблицами 'Slackbot_users' и 'Slackbot_tasks'

*Адрес и порт задаются в переменных MONGO_ADDRESS и MONGO_PORT (по умолчанию MONGO_ADDRESS='127.0.0.1'
MONGO_PORT=27017)

*Необходим токен для гугл таблиц. Он берется по адресу https://console.developers.google.com/apis/credentials и сохраняется в файле google.json

*Токен для Slack'a берется по адресу https://api.slack.com/docs/oauth и сохраняется в файле slack_token

*spreadsheetId - ID таблички в Google Spreadsheet

*channel_id - канал с заданиями в Slack

#Запуск

Программа заходит в БД, гугл таблички, и Slack. Потом читает информацию с канала с заданиями, обновляет ее в БД, после чего подключается к Google Spreadsheet и вносит изменения в таблицу. Политика при конфликте смайлов: берется более "успешный" смайл.
