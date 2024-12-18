from flask import Flask, request, abort
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime
from image.ImgProcess import Img_Process
from model.CnnModel import Load_CnnModel, Clear_model
from tensorflow.python.keras.utils import np_utils
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

def create_rich_menu():
    line_bot_api = Get_MessagingApi()
    with ApiClient(configuration) as api_client:
        line_bot_blob_api = MessagingApiBlob(api_client)

    areas=[
        RichMenuArea(
            bounds=RichMenuBounds(
                x=0,
                y=0,
                width=833,
                height=843
            ),
            action=MessageAction(text="這是A")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(
                x=833,
                y=0,
                width=833,
                height=843
            ),
            action=MessageAction(text="這是B")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(
                x=1666,
                y=0,
                width=833,
                height=843
            ),
            action=MessageAction(text="BOT 使用方法")
        )
    ]

    rich_menu_to_create = RichMenuRequest(
        size=RichMenuSize(
            width=2500,
            height=843
        ),
        selected=True,
        name="圖文選單",
        chatBarText="查看更多",
        areas=areas
    )

    rich_menu_id = line_bot_api.create_rich_menu(
        rich_menu_request=rich_menu_to_create
    ).rich_menu_id
    
    with open('./image/menu.png', 'rb') as image:
        line_bot_blob_api.set_rich_menu_image(
            rich_menu_id=rich_menu_id,
            body=bytearray(image.read()),
            _headers={'Content-Type': 'image/png'}
        )
        
    line_bot_api.set_default_rich_menu(rich_menu_id)

create_rich_menu()

@handler.add(FollowEvent)
def Say_Hello(event):
    line_bot_api = Get_MessagingApi()
    line_bot_api.reply_message(
        ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text="Hi")]
        )
    )


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
                action=PostbackAction(
                    label="開始訓練",
                    displayText="訓練開始",
                    data="Add"
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
        
    elif event.message.text == 'BOT 使用方法':
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="上傳圖片->選擇預測或訓練->模型->結果")]
            )
        )

    elif event.message.text == '預測' and file_path != "null":
        img = Img_Process(file_path)
        model = Load_CnnModel()
        result = model.predict(img)
        Clear_model(model)

        url = request.root_url.replace("http", "https")
        flex_json = json.load(open("./image/flex/ResultFlex.json", "r", encoding="utf-8"))
        for i,item in enumerate(flex_json["body"]["contents"][1]["contents"]):
            item["contents"][0]["url"]=f"{url}image/flex/{item['contents'][1]['text']}.jpg"
            item["contents"][2]["text"]=f"Percentage: {result[0][i] * 100:.2f}"
        flex_json["hero"]["url"]=f"{url}image/{file_path.split('/')[-1]}"
        flex_str = json.dumps(flex_json)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[FlexMessage(alt_text='預測結果', contents=FlexContainer.from_json(flex_str))]
            )
        )

    elif event.message.text == '預測正確' and file_path != "null":
        Confirm = ConfirmTemplate(
            text="預測正確,是否將圖片加入訓練集?",
            actions=[
                PostbackAction(label="是", data="Add", displayText="將影像用做模型訓練"),
                PostbackAction(label="否", data="Dont Add", displayText="不要將我的影像用作訓練")
            ]
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TemplateMessage(alt_text="發生錯誤!", template=Confirm)]
            )
        )

    elif event.message.text == '預測錯誤' and file_path != "null":
        Confirm = ConfirmTemplate(
            text="預測錯誤,是否將圖片加入訓練集?",
            actions=[
                PostbackAction(label="是", data="Add", displayText="將影像用做模型訓練"),
                PostbackAction(label="否", data="Dont Add", displayText="不要將我的影像用作訓練")
            ]
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TemplateMessage(alt_text="發生錯誤!", template=Confirm)]
            )
        )

    else:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="指令錯誤或尚未上傳圖片")]
            )
        )



@handler.add(PostbackEvent)
def Get_Postback(event):
    global labels
    Postback_data = event.postback.data
    line_bot_api = Get_MessagingApi()
    
    if Postback_data == "Add":
        Select_label = QuickReply(
            items=[
                QuickReplyItem(action=PostbackAction(label="貓", data="0", displayText="這是貓")),
                QuickReplyItem(action=PostbackAction(label="狗", data="1", displayText="這是狗")),
                QuickReplyItem(action=PostbackAction(label="狐狸", data="2", displayText="這是狐狸")),
                QuickReplyItem(action=PostbackAction(label="豹", data="3", displayText="這是豹")),
                QuickReplyItem(action=PostbackAction(label="獅子", data="4", displayText="這是獅子")),
                QuickReplyItem(action=PostbackAction(label="老虎", data="5", displayText="這是老虎")),
                QuickReplyItem(action=PostbackAction(label="狼", data="6", displayText="這是狼"))
            ]
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="選擇這張圖片的標籤", quickReply=Select_label)],
            )
        )

    elif Postback_data in ["0", "1", "2", "3", "4", "5", "6"]:
        label_list = ["貓", "狗", "狐", "豹", "獅子", "老虎", "狼"]
        labels = int(Postback_data)
        url = request.root_url
        url = url.replace("http", "https")
        Show_Chosen = ButtonsTemplate(
            thumbnailImageUrl=url + file_path.lstrip("./"),
            title="這是 "+ label_list[labels],
            text="正確無誤?",
            actions=[
                PostbackAction(label="正確,開始訓練", data="Start train", displayText="正確"),
                PostbackAction(label="有誤,重新選擇", data="Add", displayText="重新選擇")
            ]
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TemplateMessage(altText="ERROR", template=Show_Chosen)]
            )
        )
    
    elif Postback_data == "Start train":
        img = Img_Process(file_path)
        model = Load_CnnModel()
        labels = np_utils.to_categorical(np.array([labels]), 7)
        train_history = model.fit(img, labels, epochs=5, batch_size=1, verbose=1)
        model.save("./model/Animal_faces_CNN.h5")
        Clear_model(model)

        Show_repredict_select = QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="Yes", text="預測")),
                QuickReplyItem(action=PostbackAction(label="No", displayText="不需要", data="Exit the System"))
            ]
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="訓練完成,需要重新預測嗎?", quickReply=Show_repredict_select)]
            )
        )

    elif Postback_data == "Dont Add":
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="不加入訓練,系統結束")]
            )
        )

    else:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="系統結束")]
            )
        )

if __name__ == '__main__':
    app.run()