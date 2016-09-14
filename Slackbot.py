#!/usr/local/bin/Python3.5
import requests
import json
import time
import pymongo
import re
from apiclient import discovery
import httplib2
from oauth2client.service_account import ServiceAccountCredentials
emoji={
    "+1":"👍",
    "the_horns":"🤘",
    "sweat_smile":"😅",
    "rage":"😡",
    "ZZZ":"💤",}


#https://api.slack.com - Slack API
Slacktoken="Slack-token"
#https://api.slack.com/docs/oauth  - to get token

#https://developers.google.com/sheets/reference/query-parameters - Sheets API
Googletoken="your token"
#https://console.developers.google.com/apis/credentials - to get token
spreadsheetId="1JwA5cmuTQUWq--J0VnYKmULkcczw8YP83MHyDlf0BoE"
#id of google sheets

MONGO_ADDRESS='127.0.0.1'
MONGO_PORT=27017

channel_id="C2A76BCRZ"
#google auth
CREDENTIALS_FILE = 'google.json'

def get_channels():
    url="https://slack.com/api/channels.list?token="+Slacktoken
    r=requests.get(url)
    channels=json.loads(r.text)
    print(json.dumps(channels,indent=4, separators=(',', ': ')))

def get_channel_messages(channel_id,latest='now'):
    url="https://slack.com/api/channels.history?token="+Slacktoken+"&channel="+channel_id+"&unreads=1&pretty=1"
    r=requests.get(url)
    messages_body=json.loads(r.text)
    return messages_body["messages"], int(messages_body["unread_count_display"]), messages_body["messages"][-1]['ts']

def get_channel_history(channel_id):
    messages, unread_count, latest =get_channel_messages(channel_id)
    while(unread_count):
        new_messages, unread_count, latest =get_channel_messages(channel_id)
        messages.extend(new_messages)
        get_channel_messages(channel_id,latest)

    return messages
def get_tasks(messages):
    return [ (int(re.search('^([ТT])\d+', message['text']).group(0)[1:]),message)  for message in messages if message['type']=="message" and re.match('^([ТT])\d+', message['text'])]

def emoji_comp(reaction1,reaction2):
    emoji_rankings=["","💤","😡","😅","👍","🤘",]
    emoji_rankings.index(reaction1)
    if (emoji_rankings.index(reaction1)<emoji_rankings.index(reaction2)):
        return reaction2
    else:
        return reaction1





def save_tasks(tasks):
    for x in tasks:
        task={
            "task_id":x[0],
            "text":x[1]["text"],
            }
        try:
            task["reactions"]=x[1]["reactions"]
        except KeyError:
            task["reactions"]=""
#mongoDB code
        if tasks_db.find_one({'task_id':task['task_id']}):
            for key in task.keys():
                tasks_db.update_one({'task_id':task['task_id']},{"$set":{key:task[key]}})
        else:
            tasks_db.insert(task)
def invoke_from_json():
    f1=open("users.json","r")
    for f in f1:
        user=json.loads(f)
        users_db.insert(user)

def get_table(spreadsheetId,rangeName):
    rangeN = "Sheet1!"+rangeName
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId, range=rangeN).execute()
    values = result.get('values', [])
    return values

def put_in_table(spreadsheetId,table_range,values):

    results = service.spreadsheets().values().batchUpdate(spreadsheetId = spreadsheetId, body = {
    "valueInputOption": "USER_ENTERED",
    "data": [
        {"range": "Sheet1!"+table_range,
         "majorDimension": "ROWS",     # сначала заполнять ряды, затем столбцы (т.е. самые внутренние списки в values - это ряды)
        # "values": [["This is B2", "This is C2"], ["This is B3", "This is C3"]]}
         "values": values}
    ]
    }).execute()

def add_columns(spreadsheetId,col_numbers):
    results = service.spreadsheets().values().batchUpdate(spreadsheetId = spreadsheetId, body = {
      "requests":
        {
          "insertDimension": {
            "range": {
              "sheetId": "Sheet1!",
              "dimension": "COLUMNS",
              "startIndex": tasks_db.count()+2-col_numbers,
              "endIndex": tasks_db.count()+2
            },
            "inheritBefore": true
          }
        }
    }).execute()

def get_range(tasks_number):
    tasks_number+=2 #
    result = []
    while tasks_number:
        tasks_number, rem = divmod(tasks_number-1, 26)
        result[:0] = chr(ord("A")+rem)
    return "C4:"+''.join(result)+"59", ''.join(result)

def update_table(spreadsheetId):
    tasks_number=tasks_db.count()
    table_range, last_col=get_range(tasks_number)
    old_data=get_table(spreadsheetId,table_range)
    print (old_data[0][-2])

    insertion_number=0
    while(re.match('^([ТT])\d+', old_data[0][-1-insertion_number])==None):
        insertion_number+=1
        print(old_data[0][-1-insertion_number])
        print("we need incertion")
    print (insertion_number)

    new_data=[["" for i in range(tasks_number)] for j in range(users_db.count())]
    for task in tasks_db.find():
        for reaction in task["reactions"]:
            for user in reaction["users"]:
                if (users_db.find_one({"slack_id":user})):
                    row=int(users_db.find_one({"slack_id":user})["row"])-5
                    col=task["task_id"]
                    if(new_data[row][col]!=""):
                        if (reaction["name"] in emoji.keys()):
                            new_data[row][col]=emoji_comp(new_data[row][col],emoji[reaction["name"]])
                    else:
                        try:
                            new_data[row][col]=emoji_comp(old_data[row][col],emoji[reaction["name"]])
                        except IndexError:
                            new_data[row][col]=emoji[reaction["name"]]

    put_in_table(spreadsheetId,table_range,new_data)


if __name__ == '__main__':
    conn = pymongo.MongoClient(MONGO_ADDRESS,MONGO_PORT)
    db=conn['Slackbot']
    users_db=db['Slackbot_users']
    tasks_db=db['Slackbot_tasks']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE,'https://www.googleapis.com/auth/spreadsheets')
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,discoveryServiceUrl=discoveryUrl)

    #save_tasks(get_tasks(get_channel_history(channel_id)))
    #get_table(spreadsheetId,"B5:R59")




    update_table(spreadsheetId)
    conn.close()
