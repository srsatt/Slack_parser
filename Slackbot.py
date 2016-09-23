#!venv/bin/Python3.5
# -*- coding: utf-8 -*-
import requests
import json
import re
import collections

import pymongo
from jinja2 import Template
emoji={
    "+1":"👍",
    "the_horns":"🤘",
    "sweat_smile":"😅",
    "rage":"😡",
    "ZZZ":"💤",}

#https://api.slack.com - Slack API
#https://api.slack.com/docs/oauth  - to get token
MONGO_ADDRESS='127.0.0.1'
MONGO_PORT=27017
channel_id="C2A76BCRZ"

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
    if (latest=="now"):
        url="https://slack.com/api/channels.history?token="+Slacktoken+"&channel="+channel_id+"&unreads=1&pretty=1"
    else:
        url="https://slack.com/api/channels.history?token="+Slacktoken+"&channel="+channel_id+"&unreads=1&pretty=1&latest="+latest

    r=requests.get(url)
    messages_body=json.loads(r.text)
    try:
        return messages_body["messages"], messages_body["has_more"], messages_body["messages"][-1]["ts"]
    except IndexError:
        return messages_body["messages"], messages_body["has_more"], 0

def get_channel_history(channel_id):
    messages, has_more, latest =get_channel_messages(channel_id)
    while(has_more):
        new_messages, has_more, latest =get_channel_messages(channel_id,latest=latest)
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

def save_table(messages,table,message_name):
    for x in messages:
        message={
            message_name+"_id":int(re.search('\d+',x[0]).group(0)),
            "text":x[1]["text"],
            "user":x[1]["user"]
            }
        try:
            message["reactions"]=x[1]["reactions"]
        except KeyError:
            message["reactions"]=""
        if table.find_one({message_name+'_id':message[message_name+'_id']}):
            for key in message.keys():
                table.update_one({message_name+'_id':message[message_name+'_id']},{"$set":{key:message[key]}})
        else:
            table.insert(message)


def invoke_from_json():
    f1=open("users.json","r")
    for f in f1:
        user=json.loads(f)
        users_db.insert(user)
    f1.close()

def invoke_from_slack():
    url="https://slack.com/api/users.list?token="+Slacktoken
    r=requests.get(url)
    users=json.loads(r.text)
    for user in users['members']:
        if users_db.find_one({'user_id':user["id"]}):
            for key in user.keys():
                users_db.update_one({'user_id':user['id']},{"$set":{key:user[key]}})
        else:
            users_db.insert(user)

def get_progression():
    progression={}
    for user in users_db.find():
        if(user["name"]):
            progression[user["name"]]=[""]*tasks_db.count()
    for task in tasks_db.find():
        for reaction in task["reactions"]:
            for user in reaction["users"]:
                try:
                    progression[users_db.find_one({"id":user})["name"]][task["task_id"]]=emoji[reaction["name"]]
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

def get_project_list():
    projects={}
    for project in projects_db.find():
        projects[project["project_id"]]={
            "text":project["text"],
            "author":users_db.find_one({"id":project["user"]})['name'],
            "reactions":{reaction["name"]: [users_db.find_one({"id":user})["name"] for user in reaction["users"]] for reaction in project["reactions"]}
        }
    return projects

def render_to_file(data,filename):
    f1=open(filename,"r")
    template=Template(f1.read())
    f1.close()
    return template.render(data=data)

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
    projects_db=db['Slackbot_projects']
    invoke_from_slack()
    #save_table(messages=filter_messages(get_channel_history(channel_id),'^([TТ])\d+'),table=tasks_db,message_name="task")
    save_table(messages=filter_messages(get_channel_history('C2A5C1JBY'),'^\d+[.:]'),table=projects_db,message_name="project")
    html_projects=render_to_file(filename="projects_template.html",data=collections.OrderedDict(sorted(get_project_list().items(), key=lambda t: t[0])))
    html_table=render_to_file(filename="table_template.html",data=get_progression())
    save_tabe(filename="table.html",data=html_table)
    save_tabe(filename="projects.html",data=html_projects)
    conn.close()
