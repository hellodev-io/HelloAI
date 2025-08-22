#!/usr/bin/env python3
"""
生成默认缩略图脚本

当文章没有合适的图片时，生成默认的 HelloAI 品牌缩略图。
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def create_default_thumbnail():
    """创建默认缩略图"""
    # 创建400x300的图片
    img = Image.new('RGB', (400, 300), color='#f0f6ff')
    draw = ImageDraw.Draw(img)
    
    # 绘制简单的背景渐变效果（用矩形模拟）
    for i in range(50):
        alpha = int(255 * (1 - i/50) * 0.1)
        color = f"#{hex(240)[2:].zfill(2)}{hex(min(255, 246 + i))[2:].zfill(2)}{hex(255)[2:].zfill(2)}"
        draw.rectangle([0, i*6, 400, (i+1)*6], fill=color)
    
    # 绘制 HelloAI 文字
    try:
        # 尝试使用系统字体
        font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
        font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
    except:
        # 如果系统字体不可用，使用默认字体
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 主标题
    draw.text((200, 120), "HelloAI", fill='#2c5282', font=font_large, anchor='mm')
    
    # 副标题
    draw.text((200, 160), "AI行业日报", fill='#4a5568', font=font_small, anchor='mm')
    
    # 日期占位符
    draw.text((200, 200), "AI Daily Report", fill='#718096', font=font_small, anchor='mm')
    
    # 保存图片
    output_path = Path('config/default_thumb.jpg')
    output_path.parent.mkdir(exist_ok=True)
    img.save(output_path, 'JPEG', quality=85)
    
    print(f"默认缩略图已生成: {output_path}")


if __name__ == '__main__':
    create_default_thumbnail()