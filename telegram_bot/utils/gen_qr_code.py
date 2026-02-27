import qrcode
from PIL import Image, ImageDraw
import os

#pip install Pillow qrcode

def get_qr_code(veless_url:str)->str:

    qr = qrcode.QRCode(version=1, box_size=12, border=4)
    qr.add_data(veless_url)
    qr.make(fit=True)

    # Генерируем QR
    img = qr.make_image(fill_color="#2a5d84", back_color="white")

    # 1. ПРИВОДИМ РАЗМЕРЫ К ОДНАКОВЫМ
    img_resized = img.resize((400, 400))  # Подгоняем под ширину 400px

    # 2. Создаём заголовок
    title = Image.new('RGB', (400, 60), color='white')
    d = ImageDraw.Draw(title)
    d.text((20, 20), "🔗 VLESS QR", fill='black')

    # 3. Объединяем (400 + 400 = 860 высота)
    final_img = Image.new('RGB', (400, 460), color='white')
    final_img.paste(title, (0, 0))           # Текст сверху
    final_img.paste(img_resized, (0, 60))    # QR снизу

    # 4. Сохраняем
    output_file = 'vless_qr_pro.png'
    final_img.save(output_file, format='PNG', optimize=True)
    print(f"✅ Сохранено: {os.path.abspath(output_file)}")
    return os.path.abspath(output_file)