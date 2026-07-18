import re
import unicodedata


def normalize_query(text):
    text = unicodedata.normalize("NFKC", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_digits(text):
    return re.sub(r"[^\d]", "", text)


def safe_get(data, keys, default=""):
    for key in keys:
        try:
            data = data[key]
        except (KeyError, IndexError, TypeError):
            return default
    return data if data is not None else default


def roc_to_ad(year_roc):
    return int(year_roc) + 1911


def ad_to_roc(year_ad):
    return year_ad - 1911
