#!venv/bin/Python3
# -*- coding: utf-8 -*-
import json
import re
import collections
import os.path
import time

import schedule
import requests
import emoji
from jinja2 import Template


emoji_list={
    "+1":"👍",
    "the_horns":"🤘",
    "sweat_smile":"😅",
    "rage":"😡",
    "ZZZ":"💤",}
#https://api.slack.com - Slack API
#https://api.slack.com/docs/oauth  - to get token
tasks_channel='C2A76BCRZ'
project_channel='C2A5C1JBY'
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
        if message not in table:
            table.append(message)

def invoke_from_slack():
    url="https://slack.com/api/users.list?token="+Slacktoken
    r=requests.get(url)
    users=json.loads(r.text)
    for user in users['members']:
        if user not in users_db:
            users_db.append(user)

def user_by_id(table, id):
    for x in table:
        if x["id"]==id:
            return x


def get_progression():
    progression={}
    for user in users_db:
        if(user["name"]):
            progression[user["name"]]=[""]*len(tasks_db)
    for task in tasks_db:
        for reaction in task["reactions"]:
            for user in reaction["users"]:
                try:
                    progression[user_by_id(users_db,user)["name"]][task["task_id"]]=emoji_list[reaction["name"]]
                except KeyError:
                    pass
                except IndexError:
                    pass
    return progression

def get_project_list():
    projects={}
    for project in projects_db:
        projects[project["project_id"]]={
            "text":htmlize_links(project["text"]),
            "author":user_by_id(users_db,project["user"])['name'],
            "reactions":{emoji.emojize(":"+reaction["name"]+":", use_aliases=True): [user_by_id(users_db,user)["name"] for user in reaction["users"]] for reaction in project["reactions"]}
        }
    return projects

def hexrepl( match ):
    split=match.group()[1:-1].split(r'|')
    if len(split)==2:
        return "<a href='{adress}'>{text}<a>".format(adress=split[0],text=split[1])
    else:
        return "<a href='{adress}'>{text}<a>".format(adress=split[0],text=split[0])

def htmlize_links(string):
    p = re.compile('\<(.*?)(\|.*?)?\>')
    return p.sub(hexrepl, string)

def render_to_file(data,filename):
    f1=open(filename,"r")
    template=Template(f1.read())
    f1.close()
    return template.render(data=data)

def save_html(filename,data):
    f1=open(filename,"w")
    f1.write(data)
    f1.close()


def job():
    invoke_from_slack()
    save_table(messages=filter_messages(get_channel_history(tasks_channel),'^([TТ])\d+'),table=tasks_db,message_name="task")
    save_table(messages=filter_messages(get_channel_history(project_channel),'^\d+[.:]'),table=projects_db,message_name="project")
    html_projects=render_to_file(filename="projects_template.html",data=collections.OrderedDict(sorted(get_project_list().items(), key=lambda t: t[0])))
    html_table=render_to_file(filename="table_template.html",data=get_progression())
    save_html(filename='html/progress_table.html',data=html_table)
    save_html(filename='html/project_ideas.html',data=html_projects)



if __name__ == '__main__':
    users_db=[]
    tasks_db=[]
    projects_db=[]
    Slacktoken=get_slack_token('slack_token')
    schedule.every(3).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
