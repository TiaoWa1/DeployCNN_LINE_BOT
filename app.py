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
import time, random


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
            action=MessageAction(text="我要看範例圖片")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(
                x=833,
                y=0,
                width=833,
                height=843
            ),
            action=MessageAction(text="BOT 使用方法")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(
                x=1666,
                y=0,
                width=833,
                height=843
            ),
            action=URIAction(uri="https://github.com/TiaoWa1", label="BOT 作者資訊")
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
    
    with open('./image/menu.jpg', 'rb') as image:
        line_bot_blob_api.set_rich_menu_image(
            rich_menu_id=rich_menu_id,
            body=bytearray(image.read()),
            _headers={'Content-Type': 'image/jpeg'}
        )
        
    line_bot_api.set_default_rich_menu(rich_menu_id)

create_rich_menu()

@handler.add(FollowEvent)
def Say_Hello(event):
    Hello_text  = (
        "👋 嗨嗨～我是 動物辨識小助手\n"
        "我可以幫你辨識以下這些動物：\n"
        "🐱貓、🐶狗、🐆豹、🦁獅、🐯虎、🦊狐、🐺狼\n"
        "📸 歡迎直接傳一張圖片給我，也可以點擊範例圖片的icon或直接輸入「範例圖片」，就能看到各種動物的範例影像喔!"
    )
    line_bot_api = Get_MessagingApi()
    line_bot_api.reply_message(
        ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=Hello_text)]
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
    elif event.message.text in ['我要看範例圖片', '範例圖片']:
        Choose_Animal = QuickReply(
            items=[
                QuickReplyItem(action=PostbackAction(label="🐱貓", data="cat", displayText="我要看貓的範例圖片")),
                QuickReplyItem(action=PostbackAction(label="🐶狗", data="dog", displayText="我要看狗的範例圖片")),
                QuickReplyItem(action=PostbackAction(label="🦊狐狸", data="fox", displayText="我要看狐狸的範例圖片")),
                QuickReplyItem(action=PostbackAction(label="🐆豹", data="leopard", displayText="我要看豹的範例圖片")),
                QuickReplyItem(action=PostbackAction(label="🦁獅子", data="lion", displayText="我要看獅子的範例圖片")),
                QuickReplyItem(action=PostbackAction(label="🐯老虎", data="tiger", displayText="我要看老虎的範例圖片")),
                QuickReplyItem(action=PostbackAction(label="🐺狼", data="wolf", displayText="我要看狼的範例圖片"))
            ]
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken = event.reply_token,
                messages = [TextMessage(
                    quickReply = Choose_Animal,
                    text = "想看哪種動物的範例圖片呢？請選擇下方類別 🐾"
                )]
            )
        )

    elif event.message.text == 'BOT 使用方法':
        usage_text = (
            "📖 嗨，我是動物辨識小助手，這是我的使用流程說明：\n"
            "1️⃣ 上傳一張動物圖片\n"
            "2️⃣ 選擇【開始預測】或【開始訓練】\n"
            " 3️⃣-1️⃣預測：模型將直接預測並回傳結果\n"
            "➡模型回傳結果後選擇正確與否，可選擇是否將圖片加入訓練\n"
            " 3️⃣-2️⃣訓練：可將圖片加入模型學習\n"
            "➡選擇訓練後可以根據你傳送的圖片自行選擇標籤，就可以開始訓練了\n"
            "4️⃣ 預測或訓練完成後，可重新預測或結束\n"
            "📷 你也可以輸入「我要看範例圖片」或點擊範例圖片的icon來瀏覽七種動物範例！"
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=usage_text)]
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

        ch_animal_name = ["🐱貓", "🐶狗", "🦊狐狸", "🐆豹", "🦁獅子", "🐯老虎", "🐺狼"]
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[FlexMessage(alt_text='預測結果', contents=FlexContainer.from_json(flex_str)), TextMessage(text = f"根據你傳送的影像，這應該是隻 {ch_animal_name[np.argmax(result, axis=1)[0]]}\n我預測得正確嗎？🤔\n可以透過上方的按鈕告訴我！☝️")]
            )
        )

    elif event.message.text == '預測正確' and file_path != "null":
        # Confirm = ConfirmTemplate(
        #     text="太好了，我答對了～😎\n可以讓我把這張圖片加入訓練集，變得更聰明嗎？📈",
        #     actions=[
        #         PostbackAction(label="⭕️", data="Add", displayText="將影像用做模型訓練"),
        #         PostbackAction(label="❌", data="Dont Add", displayText="不要將我的影像用作訓練")
        #     ]
        # )
        # line_bot_api.reply_message(
        #     ReplyMessageRequest(
        #         replyToken=event.reply_token,
        #         messages=[TemplateMessage(alt_text="發生錯誤!", template=Confirm)]
        #     )
        # )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="太棒了，我答對了呢～🎯\n有需要再幫忙辨識的話，隨時再傳給我吧！🐾")]
            )
        )

    elif event.message.text == '預測錯誤' and file_path != "null":
        Confirm = ConfirmTemplate(
            text="糟糕！我答錯了😢\n要不要讓我學習一下這張圖片，下次答得更準？📚",
            actions=[
                PostbackAction(label="⭕️", data="Add", displayText="將影像用做模型訓練"),
                PostbackAction(label="❌", data="Dont Add", displayText="不要將我的影像用作訓練")
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
                messages=[TextMessage(text=f"指令錯誤或尚未上傳圖片 {file_path}")]
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
                QuickReplyItem(action=PostbackAction(label="🐱貓", data="0", displayText="這是貓")),
                QuickReplyItem(action=PostbackAction(label="🐶狗", data="1", displayText="這是狗")),
                QuickReplyItem(action=PostbackAction(label="🦊狐狸", data="2", displayText="這是狐狸")),
                QuickReplyItem(action=PostbackAction(label="🐆豹", data="3", displayText="這是豹")),
                QuickReplyItem(action=PostbackAction(label="🦁獅子", data="4", displayText="這是獅子")),
                QuickReplyItem(action=PostbackAction(label="🐯老虎", data="5", displayText="這是老虎")),
                QuickReplyItem(action=PostbackAction(label="🐺狼", data="6", displayText="這是狼"))
            ]
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="這張圖是什麼動物呢？\n幫我選一個吧～📌", quickReply=Select_label)],
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
                PostbackAction(label="✅ 確認無誤，進行訓練", data="Start train", displayText="正確"),
                PostbackAction(label="🔄 標籤不對，我要再選一次", data="Add", displayText="重新選擇")
            ]
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TemplateMessage(altText="ERROR", template=Show_Chosen)]
            )
        )
    
    elif Postback_data in ["cat", "dog", "fox", "leopard", "lion", "tiger", "wolf"]:
        animal_name = {
            "cat": "貓",
            "dog": "狗",
            "fox": "狐狸",
            "leopard": "豹",
            "lion": "獅子",
            "tiger": "老虎",
            "wolf": "狼"
        }
        rand_int = random.randint(1, 10)
        url = request.root_url.replace("http", "https")
        global img_url
        global local_img_url
        local_img_url = f"./image/random_sample_img/{Postback_data}_{rand_int}.jpg"
        img_url = url + f"/image/random_sample_img/{Postback_data}_{rand_int}.jpg"
        chinese_name = animal_name[Postback_data]
        Sample_img_predict = QuickReply(
            items=[
                QuickReplyItem(action=PostbackAction(label="Yes", displayText="用範例圖片預測一次", data="Sample Img Predict")),
                QuickReplyItem(action=PostbackAction(label="No", displayText="不需要", data="Exit the System"))
            ]
        )
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken = event.reply_token,
                messages=[
                    TextMessage(text=f"這是{chinese_name}的範例圖片 🐾"),
                    ImageMessage(originalContentUrl=img_url, previewImageUrl=img_url),
                    TextMessage(text="需要用範例圖片模擬預測一次嗎?🤔",quickReply=Sample_img_predict)
                ]
            )
        )

    elif Postback_data == "Sample Img Predict":
        img = Img_Process(local_img_url)
        model = Load_CnnModel()
        result = model.predict(img)
        Clear_model(model)

        url = request.root_url.replace("http", "https")
        flex_json = json.load(open("./image/flex/Sample_Img_Flex.json", "r", encoding="utf-8"))
        for i,item in enumerate(flex_json["body"]["contents"][1]["contents"]):
            item["contents"][0]["url"]=f"{url}image/flex/{item['contents'][1]['text']}.jpg"
            item["contents"][2]["text"]=f"Percentage: {result[0][i] * 100:.2f}"
        flex_json["hero"]["url"]=img_url
        flex_str = json.dumps(flex_json)

        ch_animal_name = ["🐱貓", "🐶狗", "🦊狐狸", "🐆豹", "🦁獅子", "🐯老虎", "🐺狼"]
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[FlexMessage(alt_text='預測結果', contents=FlexContainer.from_json(flex_str)), TextMessage(text = f"這張範例圖片預測結果為：\n{ch_animal_name[np.argmax(result, axis=1)[0]]}")]
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
                messages=[TextMessage(text="訓練完成囉！需要重新預測一次看看嗎？🔁", quickReply=Show_repredict_select)]
            )
        )

    elif Postback_data == "Dont Add":
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="好的，這張圖片就不加入訓練囉！感謝你的使用～ 😊\n等你再出題考考我～🧠")]
            )
        )

    else:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text="系統結束囉～謝謝你的使用😊")]
            )
        )

if __name__ == '__main__':
    app.run()