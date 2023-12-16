from PIL import Image

# 画像の読み込み
image_path = 'data/map3_1.png'
output_path = 'data/map3_1_data.txt'

resized_image = Image.open(image_path)

# 画像を80x80にリサイズ
#resized_image = image.resize((80, 80), Image.LANCZOS)

# ピクセルデータを取得
pixel_data = resized_image.load()

# しきい値
THRESHOLD_DEEP = 240  # 最も白い
THRESHOLD_LIGHT = 20  # 最も濃い

# 画像データを0, 1, 3, 5の配列に変換
image_array = []
for y in range(resized_image.height):
    row = []
    for x in range(resized_image.width):
        r, g, b, a = pixel_data[x, y][:4]  # RGBAまたはRGB
        # 赤の濃さに応じて値を割り当てる
        if r > THRESHOLD_DEEP:
            row.append(5)
        elif r > THRESHOLD_LIGHT:
            row.append(1)
        else:
            row.append(0)
    image_array.append(row)


# データをテキストファイルに保存

with open(output_path, 'w') as file:
    for row in image_array:
        line = ', '.join(str(val) for val in row)
        file.write(line + '\n')

print('データを保存しました:', output_path)
