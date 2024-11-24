from flask import Flask, request, abort
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime
from image.ImgProcess import Img_Process
from model.CnnModel import Load_CnnModel, Clear_model
import json, requests, os
import numpy as np
import tensorflow as tf


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

def check_gpu_memory():
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if not gpus:
        print("未偵測到 GPU")
        return
    for gpu in gpus:
        mem_info = tf.config.experimental.get_memory_info('GPU:0')
        print(f"GPU 記憶體使用狀態: {mem_info}")


app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

def Line_bot_api():
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
    line_bot_api = Line_bot_api()
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

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="影像已儲存!")
    )

@handler.add(MessageEvent, message=TextMessageContent)
def Reply_Predict_Result(event):
    line_bot_api = Line_bot_api()
    if event.message.text == '位置':
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=file_path)]
            )
        )
    if event.message.text == '預測':
        img = Img_Process("./image/Example.jpg")
        model = Load_CnnModel()
        result = model.predict(img)
        Clear_model(model)

        url = request.root_url + '/static'
        url = url.replace("http", "https")
        print(url)
        Predict_Carousel_Template = CarouselTemplate(
            columns=[
                CarouselColumn(
                    thumbnailImageUrl=url+"/cat.jpg",
                    title="Cat",
                    text="Percentage: ",
                    actions=[MessageAction(label="test",text="test")]
                ),
                CarouselColumn(
                    thumbnailImageUrl=url+"/dog.jpg",
                    title="dog",
                    text="Percentage: ",
                    actions=[MessageAction(label="test",text="test")]
                ),
                CarouselColumn(
                    thumbnailImageUrl=url+"/fox.jpg",
                    title="fox",
                    text="Percentage: ",
                    actions=[MessageAction(label="test",text="test")]
                ),
                CarouselColumn(
                    thumbnailImageUrl=url+"/leopard.jpg",
                    title="leopard",
                    text="Percentage: ",
                    actions=[MessageAction(label="test",text="test")]
                ),
                CarouselColumn(
                    thumbnailImageUrl=url+"/lion.jpg",
                    title="lion",
                    text="Percentage: ",
                    actions=[MessageAction(label="test",text="test")]
                ),
                CarouselColumn(
                    thumbnailImageUrl=url+"/tiger.jpg",
                    title="tiger",
                    text="Percentage: ",
                    actions=[MessageAction(label="test",text="test")]
                ),
                CarouselColumn(
                    thumbnailImageUrl=url+"/wolf.jpg",
                    title="wolf",
                    text="Percentage: ",
                    actions=[MessageAction(label="test",text="test")]
                )
            ]
        )
        template_message = TemplateMessage(template=Predict_Carousel_Template, altText="錯誤!")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[template_message]
            )
        )

if __name__ == '__main__':
    app.run()