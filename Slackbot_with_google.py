#!venv/bin/Python3.5
# -*- coding: utf-8 -*-
import requests
import json
import re

import pymongo
from apiclient import discovery
import httplib2
from oauth2client.service_account import ServiceAccountCredentials
from jinja2 import Template
emoji={
    "+1":"👍",
    "the_horns":"🤘",
    "sweat_smile":"😅",
    "rage":"😡",
    "ZZZ":"💤",}

#https://api.slack.com - Slack API
#https://api.slack.com/docs/oauth  - to get token
#https://developers.google.com/sheets/reference/query-parameters - Sheets API
#https://console.developers.google.com/apis/credentials - to get token
spreadsheetId="1JwA5cmuTQUWq--J0VnYKmULkcczw8YP83MHyDlf0BoE" #id of google sheets
MONGO_ADDRESS='127.0.0.1'
MONGO_PORT=27017
channel_id="C2A76BCRZ"
CREDENTIALS_FILE = 'google.json' #google auth

def get_slack_token(filename):
    f1=open(filename,"r")
    token=f1.read()[:-1]
    f1.close()
    return token

def get_channels():
    url="https://slack.com/api/channels.list?token="+Slacktoken
    r=requests.get(url)
    channels=json.loads(r.text)

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

def filter_messages(messages,regexp):
    return [ (re.search(regexp, message['text']).group(0),message)  for message in messages if message['type']=="message" and re.match(regexp,message['text'])]

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
            "task_id":int(x[0][1:]),
            "text":x[1]["text"],
            }
        try:
            task["reactions"]=x[1]["reactions"]
        except KeyError:
            task["reactions"]=""
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
    f1.close()

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
    body ={
  "requests":
    {
      "insertDimension": {
        "range": {
          "sheetId": 0,
          "dimension": "COLUMNS",
          "startIndex": 2+tasks_db.count()-col_numbers,
          "endIndex": 2+tasks_db.count()
        },
        #"inheritBefore": "true"
      }
    },
}
    service.spreadsheets().batchUpdate(spreadsheetId = spreadsheetId,body = body).execute()

def get_progression():
    progression={}
    for user in users_db.find():
        if(user["slack_name"]):
            progression[user["slack_name"]]=[""]*tasks_db.count()
    for task in tasks_db.find():
        for reaction in task["reactions"]:
            for user in reaction["users"]:
                try:
                    progression[users_db.find_one({"slack_id":user})["slack_name"]][task["task_id"]]=emoji[reaction["name"]]
                except KeyError:
                    pass
                except IndexError:
                    pass
    return progression

def get_range(tasks_number):
    tasks_number+=2 #
    result = []
    while tasks_number:
        tasks_number, rem = divmod(tasks_number-1, 26)
        result[:0] = chr(ord("A")+rem)
    return "C4:"+''.join(result)+"59", ''.join(result)

def update_table(spreadsheetId):
    tasks_number=tasks_db.count()
    table_range, last_col=get_range(tasks_db.count())
    old_data=get_table(spreadsheetId,table_range)
    new_data=[["" for i in range(tasks_number)] for j in range(55)]
    for i in range(tasks_db.count()):
        new_data[0][i]="T"+str(i+1)
    insertion_number=tasks_db.count()-old_data[0].index("SMART цель на сентябрь")

    add_columns(spreadsheetId,insertion_number)
    for task in tasks_db.find():
        for reaction in task["reactions"]:
            for user in reaction["users"]:
                if (users_db.find_one({"slack_id":user})):
                    row=int(users_db.find_one({"slack_id":user})["row"])-4
                    col=task["task_id"]
                    try:
                        if((new_data[row][col]!="") and (col<old_data[0].index("SMART цель на сентябрь")) and (reaction["name"] in emoji.keys())):
                                new_data[row][col]=emoji_comp(new_data[row][col],emoji[reaction["name"]])
                        else:
                                new_data[row][col]=emoji[reaction["name"]]
                    except KeyError:
                        pass
    put_in_table(spreadsheetId,table_range,new_data)

def make_html_table(progression):
    f1=open("template.html","r")
    template=Template(f1.read())
    f1.close()
    return template.render(progression=progression)

def save_tabe(filename,data):
    f1=open(filename,"w")
    f1.write(data)
    f1.close()

if __name__ == '__main__':
    Slacktoken=get_slack_token("slack_token")
    conn = pymongo.MongoClient(MONGO_ADDRESS,MONGO_PORT)
    db=conn['Slackbot']
    users_db=db['Slackbot_users']
    tasks_db=db['Slackbot_tasks']
    ''' #Google spreadsheets part
    credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE,'https://www.googleapis.com/auth/spreadsheets')
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,discoveryServiceUrl=discoveryUrl)
    '''
    save_tasks(filter_messages(get_channel_history(channel_id),'^([TТ])\d+'))
    html_table=make_html_table(get_progression())
    save_tabe(filename="table.html",data=html_table)
    conn.close()
