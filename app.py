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
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "flab-ejle-firebase-adminsdk-y8pnx-173ebbef59.json"
secret = "e1748f6b9e36ac6acb9d8cf853cb3f9e"
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
  'projectId': "flab-ejle",
})
db = firestore.client()


# Initializes your app with your bot token and signing secret
app = App(
    token='xoxb-2546086460-1521685558146-LBgAsTnbZhpNx8ZfP2BaQ7Ty',
    signing_secret=secret
)

# Create Flask app and enable info level logging
flask_app = Flask(__name__)
handler_event = SlackRequestHandler(app)

logging.basicConfig(level=logging.WARNING)

#create client for slack message
client = WebClient(token='xoxb-2546086460-1521685558146-LBgAsTnbZhpNx8ZfP2BaQ7Ty')

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
    # try:
    #     bot_message = body['event']['subtype']
    # except KeyError:
    #     return
    # text = (body['event']["text"])
    # word_search = re.search('申し訳ありません。(.*)はまだ追加されておりません。\n', text, re.IGNORECASE)
    # if word_search:
    #     word = word_search.group(1)
    #     attachments_json = setReply(word)
    #     userid = (body["authorizations"][0]["user_id"])
    #     say(channel=userid, blocks=attachments_json)
    # else:
    #     return
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

    # Different intent handler
    if (request_["queryResult"]["intent"]['displayName']) ==  "Slack channel":
        return {
        "fulfillmentMessages": [
        {
            "payload": {
            "slack": {
                "text":
                """
    ＜学習系＞
    <https://flect.slack.com/archives/CCKQMPQKA|#awsを学ぶ会>, <https://flect.slack.com/archives/CAFLS3DB3|#salesforceを学ぶ会>, <https://flect.slack.com/archives/C014BK6V2Q3|#azureを学ぶ会>, <https://flect.slack.com/archives/C01FGQFTCAF|#herokuを学ぶ会>
    #・・・各種サービスの情報をシェアしたり、質問を投げて助けてもらえたりするチャンネル
    <https://flect.slack.com/archives/C019CRZCSCT|#aws_rss> ・・・AWS関連のRSSを流すチャンネル（オススメのRSSあったら教えてください）
    <https://flect.slack.com/archives/C5PB2KHTR|#security> ・・・セキュリティに関することなら何でも流していくチャンネル
    <https://flect.slack.com/archives/CKC6AS3L3|#challenge_sf_certification> ・・・Salesforce認定資格を勉強する人が集まるチャンネル。困ったことを投げると回答が返ってくるので本当にありがたい
    ＊ challenge〜で始まるチャンネル名で、資格取得目指すものがいくつかあるので検索してみるとよき
    ＜雑談系＞
    <https://flect.slack.com/archives/C4VABQYA3|#ランチ> ・・・会社周辺のランチ情報をシェアするチャンネル
    <https://flect.slack.com/archives/C011D32H9RD|#zatsudan> ・・・気軽に雑談できるゆるいチャンネル。たまに通話する。リモートでさみしいときもぜひ
    <https://flect.slack.com/archives/C8YGGGZHP|#名言集> ・・・「迷言」もあるよ
    <https://flect.slack.com/archives/C016X4PST5E|#circle_バイク> （非公式サークル）・・・バイク好きあつまれ
    ＜社内サークル＞
    ちょこちょこ活動している各種サークル（気になるところには参加！！！）
    <https://flect.slack.com/archives/CE56UAED9|#circle_ボドゲ部>
    <https://flect.slack.com/archives/C5URTLYHL|#circle_ボルダリング>
    <https://flect.slack.com/archives/CHJCFK1KR|#circle_golf>
    <https://flect.slack.com/archives/C7CEQ2N82|#circle_フットサル>
    ＜趣味系＞
    <https://flect.slack.com/archives/C308YDZRB|#anime> ・・・アニメや漫画が好きな人が集うチャンネル
    <https://flect.slack.com/archives/C63C32MAN|#game> ・・・ゲーム全般。情報をシェアしたりマルチプレイの募集をしたり
    <https://flect.slack.com/archives/C624MRWP9|#yakiu> ・・・野球好きな人はここ
    <https://flect.slack.com/archives/CBVKBQJN8|#らーめんch> ・・・ラーメン好き集まれ
    <https://flect.slack.com/archives/C33RJ211S|#books> ・・・読んだ本の総評やおすすめなどを流す
    <https://flect.slack.com/archives/CQJM9DJFL|#camera> ・・・カメラ沼へようこそ
                 """
                    }
                }
            }
        ]    
    } # Don't process if the confidence level is low 
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


# slack block format
# try:
    #     attachments_json = [{
	# 		"type": "section",
	# 		"text": {
	# 			"type": "mrkdwn",
	# 			"text": "Hello, would you like to give feedback?"
	# 		}
	# 	},
	# 	{
	# 		"type": "divider"
	# 	},
	# 	{
	# 		"type": "actions",
	# 		"elements": [
	# 			{
	# 				"type": "button",
	# 				"text": {
	# 					"type": "plain_text",
	# 					"text": "Yes",
	# 				},
	# 				"value": "click_me_123"
	# 			},
	# 			{
	# 				"type": "button",
	# 				"text": {
	# 					"type": "plain_text",
	# 					"text": "No",
	# 				},
	# 				"value": "click_me_123",
	# 			}
	# 		]
	# 	}]

    # old unused code
    # agent.add(QuickReplies(quick_replies=['Yes', 'No']))
    # client.chat_postMessage(
    # channel='client.conversations_open', text="Hello, would you like to give feedback?", blocks = attachments_json)

    # old client chat model
    # response = client.chat_postMessage(
    #     channel='#dialogflowinfo',
    #     text="{}が検索されて、回答が見つかりませんでした。".format(word))
# except SlackApiError as e:
    # print(f"Got an error: {e.response['error']}")