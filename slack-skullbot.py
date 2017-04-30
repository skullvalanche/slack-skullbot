#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Skullbot - A simple SlackBot"""

import json
import os
import random
import re
import time
from sys import argv
from datetime import datetime, timedelta

from slackclient import SlackClient

try:
    RESPONSES_FILE = argv[1] + "_responses.json"
    SETTINGS_FILE = argv[1] + "_settings.json"
except:
    print("error: invalid name specified")
    print(f"usage: {argv[0]} <name>")
    print("There must be a corresponding <name>_responses.json and <name>_settings.json present.")
    exit()

if not os.path.isfile(RESPONSES_FILE):
    print(f"Invalid responses file: {RESPONSES_FILE}")
    exit()

if os.path.isfile(SETTINGS_FILE):
    with open(SETTINGS_FILE, "r") as f:
        SETTINGS = json.loads(f.read())
else:
    print(f"Invalid '{SETTINGS_FILE}' settings file.")
    exit()

SLACK_CLIENT = SlackClient(SETTINGS['SLACK_BOT_TOKEN'])
BOT_NAME = SETTINGS['BOT_NAME']
NO_REPEAT_MINUTES = int(SETTINGS['NO_REPEAT_MINUTES'])

def respond(resp, chan):
    '''send response to channel'''
    SLACK_CLIENT.api_call("chat.postMessage", channel=chan, text=resp, as_user=True)


def get_username(user_id):
    '''get username for given id'''
    api_call = SLACK_CLIENT.api_call("users.list")
    if api_call.get('ok'):
        users = api_call.get('members')
        for user in users:
            if 'name' in user and user.get('id') == user_id:
                return user.get('name')


def parse_slack_output(slack_rtm_firehose):
    '''
    Checks slack events 'firehose' for user messages,
    returns user, message, channel
    '''
    if slack_rtm_firehose and len(slack_rtm_firehose) > 0:
        for entry in slack_rtm_firehose:
            if entry and 'text' in entry:
                return entry['user'], entry['text'].strip().lower(), entry['channel']
    return None, None, None



def find_response(text):
    '''look in text for trigger, return response message'''
    with open(RESPONSES_FILE, "r") as f:
        responses = json.loads(f.read())
    for k in responses:
        if re.search(k, text):
            if isinstance(responses.get(k), list):
                message = random.choice(responses.get(k))
            else:
                message = responses.get(k)
            return message


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    if SLACK_CLIENT.rtm_connect():
        print("Skullbot connected and running!")
        LAST_MESSAGE = ['', datetime.now()-timedelta(minutes=2)]
        while True:
            USER_ID, MESSAGE, CHANNEL_ID = parse_slack_output(SLACK_CLIENT.rtm_read())
            if USER_ID and MESSAGE and CHANNEL_ID:
                RESPONSE = find_response(MESSAGE)
                USER = get_username(USER_ID)
                if RESPONSE and USER != BOT_NAME:
                    print(f"{USER}: {MESSAGE}")
                    RESPONSE = "@%s %s" % (USER, RESPONSE)
                    if RESPONSE == LAST_MESSAGE[0] and \
                        LAST_MESSAGE[1] < datetime.now()+timedelta(minutes=NO_REPEAT_MINUTES):
                        print("Too soon. Skipping repeat response.")
                        pass
                    else:
                        respond(RESPONSE, CHANNEL_ID)
                        print(f"{BOT_NAME}: {RESPONSE}")
                        LAST_MESSAGE = [RESPONSE, datetime.now()]
                else:
                    pass
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack Token?")
