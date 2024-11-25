from flask import Flask, request, abort
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime
from image.ImgProcess import Img_Process
from model.CnnModel import Load_CnnModel, Clear_model
import json, requests, os
import numpy as np
import tensorflow as tf
import time


from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, MessagingApiBlob,
    TextMessage, Emoji, VideoMessage, AudioMessage, LocationMessage, StickerMessage, ImageMessage,
    TemplateMessage, ConfirmTemplate, ButtonsTemplate, CarouselTemplate, CarouselColumn, ImageCarouselTemplate, ImageCarouselColumn,
    PostbackAction, URIAction, MessageAction, DatetimePickerAction, CameraAction, CameraRollAction, LocationAction,
    ReplyMessageRequest, ReplyMessageResponse, PushMessageRequest, BroadcastRequest, MulticastRequest,
    FlexMessage, FlexContainer, 
    QuickReply, QuickReplyItem,
    RichMenuSize, RichMenuRequest, RichMenuArea, RichMenuBounds
)

## Webhook Event
from linebot.v3.webhooks import (
    MessageEvent, FollowEvent, PostbackEvent, TextMessageContent, ImageMessageContent
)


app = Flask(__name__, static_url_path='/image', static_folder='./image')

CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

def Get_MessagingApi():
    with ApiClient(configuration) as api_client:
        return MessagingApi(api_client)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(FollowEvent)
def Say_Hello(event):
    line_bot_api = Get_MessagingApi()
    line_bot_api.reply_message(
        ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text="Hi")]
        )
    )

global file_path
file_path = "null"

@handler.add(MessageEvent, message=ImageMessageContent)
def Image_message_received(event):
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
    UPLOAD_FOLDER = "./image/"
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)

    global file_path
    file_path = os.path.join(UPLOAD_FOLDER, f"{current_time}.jpg")
    with open(file_path, 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    line_bot_api = Get_MessagingApi()
    SelectAction = QuickReply(
        items=[
            QuickReplyItem(
                action=MessageAction(
                    label="開始預測",
                    text="預測"
                )
            ),
            QuickReplyItem(
                action=MessageAction(
                    label="查看檔案位置",
                    text="位置"
                )
            )
        ]
    )
    
    line_bot_api.reply_message(
        ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(
                quickReply=SelectAction,
                text="收到圖片了,請選擇下一步"
            )]
        )
    )

@handler.add(MessageEvent, message=TextMessageContent)
def Reply_Predict_Result(event):
    line_bot_api = Get_MessagingApi()

    if event.message.text == '位置':
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=file_path)]
            )
        )
    elif event.message.text == '預測' and file_path != "null":
        img = Img_Process(file_path)
        model = Load_CnnModel()
        result = model.predict(img)
        Clear_model(model)

        url = request.root_url
        url = url.replace("http", "https")
        flex_json = {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": url + file_path.lstrip("./"),
                        "size": "full",
                        "aspectRatio": "20:13",
                        "aspectMode": "cover",
                        "action": {
                        "type": "uri",
                        "label": "Action",
                        "uri": "https://linecorp.com"
                        }
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "md",
                        "action": {
                        "type": "uri",
                        "label": "Action",
                        "uri": "https://linecorp.com"
                        },
                        "contents": [
                        {
                            "type": "text",
                            "text": "Prediction results",
                            "weight": "bold",
                            "size": "xl",
                            "contents": []
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                {
                                    "type": "icon",
                                    "url": url + "image/flex/cat.jpg",
                                    "size": "xl"
                                },
                                {
                                    "type": "text",
                                    "text": "Cat",
                                    "weight": "bold",
                                    "flex": 0,
                                    "margin": "sm",
                                    "contents": []
                                },
                                {
                                    "type": "text",
                                    "text": f"Percentage: { result[0][0] * 100:.2f}",
                                    "size": "sm",
                                    "color": "#AAAAAA",
                                    "align": "end",
                                    "contents": []
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                {
                                    "type": "icon",
                                    "url": url + "image/flex/dog.jpg",
                                    "size": "xl"
                                },
                                {
                                    "type": "text",
                                    "text": "Dog",
                                    "weight": "bold",
                                    "flex": 0,
                                    "margin": "sm",
                                    "contents": []
                                },
                                {
                                    "type": "text",
                                    "text": f"Percentage: { result[0][1] * 100:.2f}",
                                    "size": "sm",
                                    "color": "#AAAAAA",
                                    "align": "end",
                                    "contents": []
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                {
                                    "type": "icon",
                                    "url": url + "image/flex/fox.jpg",
                                    "size": "xl"
                                },
                                {
                                    "type": "text",
                                    "text": "Fox",
                                    "weight": "bold",
                                    "flex": 0,
                                    "margin": "sm",
                                    "contents": []
                                },
                                {
                                    "type": "text",
                                    "text": f"Percentage: { result[0][2] * 100:.2f}",
                                    "size": "sm",
                                    "color": "#AAAAAA",
                                    "align": "end",
                                    "contents": []
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                {
                                    "type": "icon",
                                    "url": url + "image/flex/leopard.jpg",
                                    "size": "xl"
                                },
                                {
                                    "type": "text",
                                    "text": "Leopard",
                                    "weight": "bold",
                                    "flex": 0,
                                    "margin": "sm",
                                    "contents": []
                                },
                                {
                                    "type": "text",
                                    "text": f"Percentage: { result[0][3] * 100:.2f}",
                                    "size": "sm",
                                    "color": "#AAAAAA",
                                    "align": "end",
                                    "contents": []
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                {
                                    "type": "icon",
                                    "url": url + "image/flex/lion.jpg",
                                    "size": "xl"
                                },
                                {
                                    "type": "text",
                                    "text": "Lion",
                                    "weight": "bold",
                                    "flex": 0,
                                    "margin": "sm",
                                    "contents": []
                                },
                                {
                                    "type": "text",
                                    "text": f"Percentage: { result[0][4] * 100:.2f}",
                                    "size": "sm",
                                    "color": "#AAAAAA",
                                    "align": "end",
                                    "contents": []
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                {
                                    "type": "icon",
                                    "url": url + "image/flex/tiger.jpg",
                                    "size": "xl"
                                },
                                {
                                    "type": "text",
                                    "text": "Tiger",
                                    "weight": "bold",
                                    "flex": 0,
                                    "margin": "sm",
                                    "contents": []
                                },
                                {
                                    "type": "text",
                                    "text": f"Percentage: { result[0][5] * 100:.2f}",
                                    "size": "sm",
                                    "color": "#AAAAAA",
                                    "align": "end",
                                    "contents": []
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                {
                                    "type": "icon",
                                    "url": url + "image/flex/wolf.jpg",
                                    "size": "xl"
                                },
                                {
                                    "type": "text",
                                    "text": "Wolf",
                                    "weight": "bold",
                                    "flex": 0,
                                    "margin": "sm",
                                    "contents": []
                                },
                                {
                                    "type": "text",
                                    "text": f"Percentage: { result[0][6] * 100:.2f}",
                                    "size": "sm",
                                    "color": "#AAAAAA",
                                    "align": "end",
                                    "contents": []
                                }
                                ]
                            }
                            ]
                        }
                        ]
                    },
                    "footer": {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "message",
                                    "label": "Correct",
                                    "text": "正確"
                                },
                                "color": "#905C44",
                                "style": "primary",
                                "flex": 1
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "message",
                                    "label": "Incorrect",
                                    "text": "不正確"
                                },
                                "color": "#905C44",
                                "style": "primary",
                                "flex": 1
                            }
                        ],
                        "spacing": "md",
                        "justifyContent": "space-between"
                    }
                }
        flex_str = json.dumps(flex_json) 
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[FlexMessage(alt_text='預測結果', contents=FlexContainer.from_json(flex_str))]
            )
        )
    else:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="指令錯誤或尚未上傳圖片")]
            )
        )

if __name__ == '__main__':
    app.run()