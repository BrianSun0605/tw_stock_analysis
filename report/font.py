import os
import shutil


def get_chinese_font():
    font_path = None
    candidates = [
        "/mnt/c/Windows/Fonts/msjh.ttc",
        "/mnt/c/Windows/Fonts/msjhbd.ttc",
        "/mnt/c/Windows/Fonts/simsun.ttc",
        "/mnt/c/Windows/Fonts/mingliu.ttc",
        "/mnt/c/Windows/Fonts/NotoSansTC-VF.ttf",
        "/mnt/c/Windows/Fonts/STKAITI.TTF",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        os.path.expanduser("~/.fonts/NotoSansTC-Regular.otf"),
    ]
    for c in candidates:
        if os.path.exists(c):
            font_path = c
            break
    return font_path
