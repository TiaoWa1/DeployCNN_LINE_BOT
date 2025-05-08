from PIL import Image

img = Image.open("./image/menu.png")
img = img.convert("RGB")  # 若是 PNG 帶透明層會出錯，先轉 RGB
img.save("./image/menu_compressed.jpg", "JPEG", quality=85)