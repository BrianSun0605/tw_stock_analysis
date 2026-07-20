import os

from config import PDF_FONT_PATH


def get_chinese_font():
    """Return an existing CJK font path on native Windows, WSL, or Linux."""
    windows_dir = os.environ.get("WINDIR", r"C:\Windows")
    candidates = [
        PDF_FONT_PATH,
        os.path.join(os.path.dirname(PDF_FONT_PATH), "NotoSansTC-Variable.ttf"),
        os.path.join(windows_dir, "Fonts", "msjh.ttc"),
        os.path.join(windows_dir, "Fonts", "msjhbd.ttc"),
        os.path.join(windows_dir, "Fonts", "mingliu.ttc"),
        "/mnt/c/Windows/Fonts/msjh.ttc",
        "/mnt/c/Windows/Fonts/msjhbd.ttc",
        "/mnt/c/Windows/Fonts/mingliu.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        os.path.expanduser("~/.fonts/NotoSansTC-Regular.otf"),
    ]
    return next((path for path in candidates if path and os.path.isfile(path)), None)
