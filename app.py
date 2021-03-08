from logging import INFO
from typing import Dict

from flask import Flask, request
from flask.logging import create_logger

import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from slack import WebClient
import difflib

#bolt is for event handler
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack.errors import SlackApiError
import logging
import re
import math

logging.basicConfig(level=logging.DEBUG)

# First setup all credentials for google, dialogflow and slack. Since using cloud storage is tricky, everything 
# hard coded 
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "replace with your own json"
secret = "your secret string"
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
  'projectId': "your project id",
})
db = firestore.client()


# Initializes your app with your bot token and signing secret
app = App(
    token='replace-with-your-own-token',
    signing_secret=secret
)

# Create Flask app and enable info level logging
flask_app = Flask(__name__)
handler_event = SlackRequestHandler(app)

logging.basicConfig(level=logging.WARNING)

#create client for slack message
client = WebClient(token='replace-with-your-own-token')

#set up evengt adaptor for slack event
BOT_ID = client.api_call("auth.test")["user_id"]
phrase = ""

# @app.middleware  # or app.use(log_request)
# def log_request(logger, body, next):
#     logger.debug(body)
#     return next()

#the event listener for user opend app
@app.event("app_home_opened")
def message(payload):
    pass

def setReply(word):
    attachments_json = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "開発者を知らせたい時をボタンを押してください"},
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "{}".format(word)},
                "action_id": "button_click",
                "value" : word
            }
        }
    ]
    return attachments_json

# this monitors message in general, not needed because the intent is detected directly
@app.event("message")
def just_ack(logger, body, say):
    pass

@app.action("button_click")
def action_button_click(body, ack, say):
    # Acknowledge the action
    word = (body["actions"][0]["value"])
    ack()
    say(channel="dialogflowinfo", text="{}が検索されて、回答が見つかりませんでした。".format(word))

@flask_app.route("/1", methods=["POST"])
def slack_events():
    return handler_event.handle(request)


#rewritten how request is handled, removed agent paramter, now forces to return payload message
def handler(request_, channel) :
    search = (request_["queryResult"]["parameters"]["any"])
    q_ref = db.collection(u'questions')
    query_ref = q_ref.where(u'Term', u'==', search)
    if not query_ref.get():
        final_response = fallback_handler(search)
        attachments_json = setReply(search)
        client.chat_postMessage(
        channel=channel, text="", blocks = attachments_json)
    else:
        final_response = success_handler(search)
    return final_response


def success_handler(word):
    query_ref2 = db.collection(u'questions').where(u'Term', u'==', word).stream()
    for doc in query_ref2:
        success_phrase = (doc.to_dict()["Definition"]) + "\n"
        if (doc.to_dict()["Note"]):
            if ((doc.to_dict()["Note"]!=doc.to_dict()["Note"])) == False:
                success_phrase = success_phrase + "\n" + (doc.to_dict()["Note"]) + "\n"
    success_phrase += ('他質問ございますでしょうか？')
    return (returnMessage(success_phrase))

def fallback_handler(word):
    docs = db.collection('questions').stream()
    #store all the definition as list
    entries = []
    for doc in docs:
        entries.append(doc.to_dict()['Term'])
    phrase = '申し訳ありません。{}はまだ追加されておりません。\n'.format(word)
    closeMatch = difflib.get_close_matches(word, entries)
    if closeMatch:
        return returnMessage('{}質問リストに追加されている一番近い単語は{}です。'.format(phrase, closeMatch))
    else:
        return (returnMessage(phrase))


@flask_app.route('/', methods=['POST'])
def webhook() -> Dict:
    """Handle webhook requests from Dialogflow."""
    # Get WebhookRequest object
    request_ = request.get_json(force=True)
    try:
        channel = (request_["originalDetectIntentRequest"]["payload"]["data"]["event"]["channel"])
    except KeyError:
        return ("Something went wrong")

    # Log request headers and body
    #logger.info(f'Request headers: {dict(request.headers)}')
    #logger.info(f'Request body: {request_}')

 # Don't process if the confidence level is low 
    elif (request_["queryResult"]['intentDetectionConfidence'] <= 0.5) :
        response = returnMessage('この質問を答える自信がありません。')
        return response
    else:
        return_message = handler(request_, channel)
        return return_message

def returnMessage(phrase): 
    text = {
            "fulfillmentMessages": [{"payload": {"slack": {"text": phrase}}}]
            }
    return text

if __name__ == '__main__':
    flask_app.run(debug=True)
