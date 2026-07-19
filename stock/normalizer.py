import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import requests
from config import HEADERS, TIMEOUT
from utils.logger import get_logger

logger = get_logger(__name__)

TAIPEI_TIMEZONE = timezone(timedelta(hours=8))

TWSE_COMPANY_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_COMPANY_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
TPEX_EMERGING_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_R"
TWSE_FUND_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap47_L"
TPEX_ETF_URL = "https://www.tpex.org.tw/www/zh-tw/ETFReport/monthly"
TWSE_DAILY_SECURITIES_URL = (
    "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
)
TPEX_DAILY_SECURITIES_URL = (
    "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
)
TWSE_ETN_URLS = {
    "domestic": "https://www.twse.com.tw/rwd/zh/ETN/domestic?response=json",
    "foreign": "https://www.twse.com.tw/rwd/zh/ETN/foreign?response=json",
    "lever_inverse": ("https://www.twse.com.tw/rwd/zh/ETN/leverInverse?response=json"),
    "strategy": "https://www.twse.com.tw/rwd/zh/ETN/strategy?response=json",
}

STOCK_DB = {
    "1101": {
        "name": "台泥",
        "industry": "水泥",
        "market": "上市",
        "aliases": ["Taiwan Cement"],
    },
    "1102": {"name": "亞泥", "industry": "水泥", "market": "上市", "aliases": []},
    "1201": {"name": "味全", "industry": "食品", "market": "上市", "aliases": []},
    "1210": {"name": "大成", "industry": "食品", "market": "上市", "aliases": []},
    "1216": {
        "name": "統一",
        "industry": "食品",
        "market": "上市",
        "aliases": ["Uni-President"],
    },
    "1301": {
        "name": "台塑",
        "industry": "塑膠",
        "market": "上市",
        "aliases": ["Formosa Plastics"],
    },
    "1303": {
        "name": "南亞",
        "industry": "塑膠",
        "market": "上市",
        "aliases": ["Nan Ya"],
    },
    "1326": {
        "name": "台化",
        "industry": "塑膠",
        "market": "上市",
        "aliases": ["Formosa Chemicals"],
    },
    "1402": {"name": "遠東新", "industry": "紡織", "market": "上市", "aliases": []},
    "1434": {"name": "福懋", "industry": "紡織", "market": "上市", "aliases": []},
    "1476": {"name": "儒鴻", "industry": "紡織", "market": "上市", "aliases": []},
    "1477": {"name": "聚陽", "industry": "紡織", "market": "上市", "aliases": []},
    "1504": {"name": "東元", "industry": "機電", "market": "上市", "aliases": []},
    "1536": {"name": "和大", "industry": "汽車零件", "market": "上市", "aliases": []},
    "1605": {"name": "華新", "industry": "電線電纜", "market": "上市", "aliases": []},
    "1707": {"name": "葡萄王", "industry": "生技", "market": "上市", "aliases": []},
    "1722": {"name": "台肥", "industry": "化工", "market": "上市", "aliases": []},
    "1762": {"name": "中化生", "industry": "生技", "market": "上市", "aliases": []},
    "1789": {"name": "神隆", "industry": "生技", "market": "上市", "aliases": []},
    "1907": {"name": "永豐餘", "industry": "造紙", "market": "上市", "aliases": []},
    "2002": {
        "name": "中鋼",
        "industry": "鋼鐵",
        "market": "上市",
        "aliases": ["China Steel"],
    },
    "2006": {"name": "東和鋼鐵", "industry": "鋼鐵", "market": "上市", "aliases": []},
    "2014": {"name": "中鴻", "industry": "鋼鐵", "market": "上市", "aliases": []},
    "2027": {"name": "大成鋼", "industry": "鋼鐵", "market": "上市", "aliases": []},
    "2049": {"name": "上銀", "industry": "機械", "market": "上市", "aliases": []},
    "2059": {"name": "川湖", "industry": "電子零組件", "market": "上市", "aliases": []},
    "2062": {"name": "橋椿", "industry": "機械", "market": "上市", "aliases": []},
    "2105": {"name": "正新", "industry": "橡膠", "market": "上市", "aliases": []},
    "2204": {"name": "中華車", "industry": "汽車", "market": "上市", "aliases": []},
    "2207": {"name": "和泰車", "industry": "汽車", "market": "上市", "aliases": []},
    "2228": {"name": "劍麟", "industry": "汽車零件", "market": "上市", "aliases": []},
    "2231": {"name": "為升", "industry": "汽車零件", "market": "上市", "aliases": []},
    "2301": {
        "name": "光寶科",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": ["Lite-On"],
    },
    "2303": {
        "name": "聯電",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["UMC"],
    },
    "2308": {
        "name": "台達電",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": ["Delta Electronics"],
    },
    "2317": {
        "name": "鴻海",
        "industry": "電子代工",
        "market": "上市",
        "aliases": ["Hon Hai", "Foxconn"],
    },
    "2324": {
        "name": "仁寶",
        "industry": "電子代工",
        "market": "上市",
        "aliases": ["Compal"],
    },
    "2327": {
        "name": "國巨",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": ["Yageo"],
    },
    "2330": {
        "name": "台積電",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["TSMC", "台GG"],
    },
    "2331": {"name": "精英", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "2347": {
        "name": "聯強",
        "industry": "電子通路",
        "market": "上市",
        "aliases": ["Synnex"],
    },
    "2353": {
        "name": "宏碁",
        "industry": "電腦週邊",
        "market": "上市",
        "aliases": ["Acer"],
    },
    "2354": {"name": "鴻準", "industry": "電子零組件", "market": "上市", "aliases": []},
    "2356": {"name": "英業達", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "2357": {
        "name": "華碩",
        "industry": "電腦週邊",
        "market": "上市",
        "aliases": ["ASUS"],
    },
    "2360": {"name": "致茂", "industry": "電子測試", "market": "上市", "aliases": []},
    "2376": {
        "name": "技嘉",
        "industry": "電腦週邊",
        "market": "上市",
        "aliases": ["Gigabyte"],
    },
    "2377": {
        "name": "微星",
        "industry": "電腦週邊",
        "market": "上市",
        "aliases": ["MSI"],
    },
    "2379": {
        "name": "瑞昱",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["Realtek"],
    },
    "2382": {
        "name": "廣達",
        "industry": "電腦週邊",
        "market": "上市",
        "aliases": ["Quanta"],
    },
    "2383": {
        "name": "台光電",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "2385": {"name": "群光", "industry": "電子零組件", "market": "上市", "aliases": []},
    "2395": {
        "name": "研華",
        "industry": "工業電腦",
        "market": "上市",
        "aliases": ["Advantech"],
    },
    "2408": {
        "name": "南亞科",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["Nanya Tech"],
    },
    "2409": {"name": "友達", "industry": "面板", "market": "上市", "aliases": ["AUO"]},
    "2412": {
        "name": "中華電",
        "industry": "電信",
        "market": "上市",
        "aliases": ["CHT"],
    },
    "2449": {"name": "京元電子", "industry": "半導體", "market": "上市", "aliases": []},
    "2454": {
        "name": "聯發科",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["MediaTek", "MTK"],
    },
    "2458": {"name": "義隆", "industry": "半導體", "market": "上市", "aliases": []},
    "2474": {"name": "可成", "industry": "電子零組件", "market": "上市", "aliases": []},
    "2481": {"name": "強茂", "industry": "半導體", "market": "上市", "aliases": []},
    "2492": {
        "name": "華新科",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "2498": {
        "name": "宏達電",
        "industry": "手機",
        "market": "上市",
        "aliases": ["HTC"],
    },
    "2501": {"name": "國建", "industry": "營建", "market": "上市", "aliases": []},
    "2548": {"name": "華固", "industry": "營建", "market": "上市", "aliases": []},
    "2603": {
        "name": "長榮",
        "industry": "航運",
        "market": "上市",
        "aliases": ["Evergreen"],
    },
    "2609": {
        "name": "陽明",
        "industry": "航運",
        "market": "上市",
        "aliases": ["Yang Ming"],
    },
    "2615": {
        "name": "萬海",
        "industry": "航運",
        "market": "上市",
        "aliases": ["Wan Hai"],
    },
    "2618": {
        "name": "長榮航",
        "industry": "航運",
        "market": "上市",
        "aliases": ["EVA Air"],
    },
    "2633": {"name": "台灣高鐵", "industry": "航運", "market": "上市", "aliases": []},
    "2801": {"name": "彰銀", "industry": "金融", "market": "上市", "aliases": []},
    "2809": {"name": "京城銀行", "industry": "金融", "market": "上市", "aliases": []},
    "2812": {"name": "台中銀行", "industry": "金融", "market": "上市", "aliases": []},
    "2823": {"name": "中壽", "industry": "金融", "market": "上市", "aliases": []},
    "2834": {"name": "臺企銀", "industry": "金融", "market": "上市", "aliases": []},
    "2880": {"name": "華南金", "industry": "金融", "market": "上市", "aliases": []},
    "2881": {
        "name": "富邦金",
        "industry": "金融",
        "market": "上市",
        "aliases": ["Fubon"],
    },
    "2882": {
        "name": "國泰金",
        "industry": "金融",
        "market": "上市",
        "aliases": ["Cathay"],
    },
    "2883": {"name": "開發金", "industry": "金融", "market": "上市", "aliases": []},
    "2884": {"name": "玉山金", "industry": "金融", "market": "上市", "aliases": []},
    "2885": {"name": "元大金", "industry": "金融", "market": "上市", "aliases": []},
    "2886": {"name": "兆豐金", "industry": "金融", "market": "上市", "aliases": []},
    "2887": {"name": "台新金", "industry": "金融", "market": "上市", "aliases": []},
    "2888": {"name": "新光金", "industry": "金融", "market": "上市", "aliases": []},
    "2890": {"name": "永豐金", "industry": "金融", "market": "上市", "aliases": []},
    "2891": {
        "name": "中信金",
        "industry": "金融",
        "market": "上市",
        "aliases": ["CTBC"],
    },
    "2892": {"name": "第一金", "industry": "金融", "market": "上市", "aliases": []},
    "2903": {"name": "遠百", "industry": "貿易百貨", "market": "上市", "aliases": []},
    "2912": {
        "name": "統一超",
        "industry": "貿易百貨",
        "market": "上市",
        "aliases": ["7-Eleven"],
    },
    "3005": {"name": "神基", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "3008": {
        "name": "大立光",
        "industry": "光電",
        "market": "上市",
        "aliases": ["Largan"],
    },
    "3017": {"name": "奇鋐", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3019": {"name": "亞光", "industry": "光電", "market": "上市", "aliases": []},
    "3023": {"name": "信邦", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3026": {
        "name": "禾伸堂",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "3029": {"name": "零壹", "industry": "資訊服務", "market": "上市", "aliases": []},
    "3034": {
        "name": "聯詠",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["Novatek"],
    },
    "3036": {"name": "文曄", "industry": "電子通路", "market": "上市", "aliases": []},
    "3037": {"name": "欣興", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3044": {"name": "健鼎", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3045": {
        "name": "台灣大",
        "industry": "電信",
        "market": "上市",
        "aliases": ["Taiwan Mobile"],
    },
    "3048": {"name": "益登", "industry": "電子通路", "market": "上市", "aliases": []},
    "3050": {"name": "鈺德", "industry": "光電", "market": "上市", "aliases": []},
    "3057": {"name": "喬鼎", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "3060": {"name": "銘異", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "3090": {
        "name": "日電貿",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "3189": {"name": "景碩", "industry": "半導體", "market": "上市", "aliases": []},
    "3209": {"name": "全科", "industry": "電子通路", "market": "上市", "aliases": []},
    "3229": {"name": "晟鈦", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3231": {
        "name": "緯創",
        "industry": "電腦週邊",
        "market": "上市",
        "aliases": ["Wistron"],
    },
    "3260": {"name": "威剛", "industry": "半導體", "market": "上市", "aliases": []},
    "3406": {"name": "玉晶光", "industry": "光電", "market": "上市", "aliases": []},
    "3413": {"name": "京鼎", "industry": "半導體", "market": "上市", "aliases": []},
    "3443": {
        "name": "創意",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["Global Unichip"],
    },
    "3450": {"name": "聯鈞", "industry": "半導體", "market": "上市", "aliases": []},
    "3454": {"name": "晶睿", "industry": "光電", "market": "上市", "aliases": []},
    "3481": {
        "name": "群創",
        "industry": "面板",
        "market": "上市",
        "aliases": ["Innolux"],
    },
    "3504": {"name": "揚明光", "industry": "光電", "market": "上市", "aliases": []},
    "3515": {"name": "華擎", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "3529": {"name": "力旺", "industry": "半導體", "market": "上櫃", "aliases": []},
    "3532": {"name": "台勝科", "industry": "半導體", "market": "上市", "aliases": []},
    "3533": {"name": "嘉澤", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3545": {"name": "敦泰", "industry": "半導體", "market": "上市", "aliases": []},
    "3583": {"name": "辛耘", "industry": "半導體", "market": "上市", "aliases": []},
    "3587": {"name": "閎康", "industry": "半導體", "market": "上櫃", "aliases": []},
    "3596": {"name": "智易", "industry": "通訊", "market": "上市", "aliases": []},
    "3622": {"name": "洋華", "industry": "光電", "market": "上市", "aliases": []},
    "3645": {"name": "達邁", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3653": {"name": "健策", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3661": {
        "name": "世芯-KY",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["Alchip"],
    },
    "3673": {"name": "TPK-KY", "industry": "光電", "market": "上市", "aliases": []},
    "3686": {"name": "達能", "industry": "半導體", "market": "上市", "aliases": []},
    "3694": {"name": "海華", "industry": "通訊", "market": "上市", "aliases": []},
    "3702": {
        "name": "大聯大",
        "industry": "電子通路",
        "market": "上市",
        "aliases": ["WPG"],
    },
    "3703": {"name": "欣陸", "industry": "營建", "market": "上市", "aliases": []},
    "3704": {"name": "合勤控", "industry": "通訊", "market": "上市", "aliases": []},
    "3706": {"name": "神達", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "4105": {"name": "台灣東洋", "industry": "生技", "market": "上櫃", "aliases": []},
    "4123": {"name": "晟德", "industry": "生技", "market": "上櫃", "aliases": []},
    "4133": {"name": "亞諾法", "industry": "生技", "market": "上櫃", "aliases": []},
    "4142": {"name": "國光生", "industry": "生技", "market": "上市", "aliases": []},
    "4162": {"name": "智擎", "industry": "生技", "market": "上櫃", "aliases": []},
    "4174": {"name": "浩鼎", "industry": "生技", "market": "上櫃", "aliases": []},
    "4722": {"name": "國精化", "industry": "化工", "market": "上市", "aliases": []},
    "4737": {"name": "華廣", "industry": "生技", "market": "上市", "aliases": []},
    "4746": {"name": "台耀", "industry": "生技", "market": "上市", "aliases": []},
    "4768": {"name": "晶呈科技", "industry": "化工", "market": "上櫃", "aliases": []},
    "4904": {
        "name": "遠傳",
        "industry": "電信",
        "market": "上市",
        "aliases": ["Far EasTone"],
    },
    "4915": {"name": "致伸", "industry": "電子零組件", "market": "上市", "aliases": []},
    "4927": {
        "name": "泰鼎-KY",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "4938": {
        "name": "和碩",
        "industry": "電子代工",
        "market": "上市",
        "aliases": ["Pegatron"],
    },
    "4958": {
        "name": "臻鼎-KY",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "4966": {
        "name": "譜瑞-KY",
        "industry": "半導體",
        "market": "上櫃",
        "aliases": ["Parade"],
    },
    "4977": {"name": "眾達-KY", "industry": "通訊", "market": "上市", "aliases": []},
    "4986": {"name": "耕進", "industry": "電子零組件", "market": "上市", "aliases": []},
    "4994": {"name": "傳奇", "industry": "遊戲", "market": "上櫃", "aliases": []},
    "5007": {"name": "三星科技", "industry": "鋼鐵", "market": "上市", "aliases": []},
    "5203": {"name": "訊連", "industry": "資訊服務", "market": "上市", "aliases": []},
    "5269": {"name": "祥碩", "industry": "半導體", "market": "上市", "aliases": []},
    "5274": {"name": "信驊", "industry": "半導體", "market": "上櫃", "aliases": []},
    "5285": {"name": "界霖", "industry": "半導體", "market": "上市", "aliases": []},
    "5288": {
        "name": "豐祥-KY",
        "industry": "汽車零件",
        "market": "上市",
        "aliases": [],
    },
    "5299": {"name": "杰力", "industry": "半導體", "market": "上櫃", "aliases": []},
    "5306": {"name": "訊連", "industry": "資訊服務", "market": "上櫃", "aliases": []},
    "5347": {
        "name": "世界",
        "industry": "半導體",
        "market": "上櫃",
        "aliases": ["Vanguard"],
    },
    "5371": {"name": "中光電", "industry": "光電", "market": "上櫃", "aliases": []},
    "5425": {"name": "台半", "industry": "半導體", "market": "上櫃", "aliases": []},
    "5434": {"name": "崇越", "industry": "電子通路", "market": "上櫃", "aliases": []},
    "5469": {
        "name": "瀚宇博",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "5471": {"name": "松翰", "industry": "半導體", "market": "上市", "aliases": []},
    "5483": {"name": "中美晶", "industry": "半導體", "market": "上櫃", "aliases": []},
    "5519": {"name": "隆大", "industry": "營建", "market": "上市", "aliases": []},
    "5522": {"name": "遠雄", "industry": "營建", "market": "上市", "aliases": []},
    "5531": {"name": "鄉林", "industry": "營建", "market": "上市", "aliases": []},
    "5534": {"name": "長虹", "industry": "營建", "market": "上市", "aliases": []},
    "5608": {"name": "四維航", "industry": "航運", "market": "上市", "aliases": []},
    "5706": {"name": "鳳凰", "industry": "觀光", "market": "上市", "aliases": []},
    "5871": {"name": "中租-KY", "industry": "金融", "market": "上市", "aliases": []},
    "5876": {"name": "上海商銀", "industry": "金融", "market": "上市", "aliases": []},
    "5880": {"name": "合庫金", "industry": "金融", "market": "上市", "aliases": []},
    "5904": {"name": "寶雅", "industry": "貿易百貨", "market": "上櫃", "aliases": []},
    "5906": {
        "name": "台南-KY",
        "industry": "貿易百貨",
        "market": "上櫃",
        "aliases": [],
    },
    "6005": {"name": "群益證", "industry": "金融", "market": "上市", "aliases": []},
    "6024": {"name": "群益期", "industry": "金融", "market": "上市", "aliases": []},
    "6108": {"name": "競國", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6116": {"name": "彩晶", "industry": "面板", "market": "上市", "aliases": []},
    "6121": {"name": "新普", "industry": "電腦週邊", "market": "上櫃", "aliases": []},
    "6139": {"name": "亞翔", "industry": "機電", "market": "上市", "aliases": []},
    "6147": {"name": "頎邦", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6166": {"name": "凌華", "industry": "工業電腦", "market": "上市", "aliases": []},
    "6176": {"name": "瑞儀", "industry": "光電", "market": "上市", "aliases": []},
    "6182": {"name": "合晶", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6191": {
        "name": "精成科",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "6196": {"name": "帆宣", "industry": "半導體", "market": "上市", "aliases": []},
    "6202": {"name": "盛群", "industry": "半導體", "market": "上市", "aliases": []},
    "6213": {"name": "聯茂", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6224": {"name": "聚鼎", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6230": {"name": "超眾", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "6239": {"name": "力成", "industry": "半導體", "market": "上市", "aliases": []},
    "6244": {"name": "茂迪", "industry": "光電", "market": "上櫃", "aliases": []},
    "6257": {"name": "矽格", "industry": "半導體", "market": "上市", "aliases": []},
    "6269": {"name": "台郡", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6271": {"name": "同欣電", "industry": "半導體", "market": "上市", "aliases": []},
    "6274": {"name": "台燿", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6278": {
        "name": "台表科",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "6282": {"name": "康舒", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6285": {"name": "啟碁", "industry": "通訊", "market": "上市", "aliases": []},
    "6409": {"name": "旭隼", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6412": {"name": "群電", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6414": {"name": "樺漢", "industry": "工業電腦", "market": "上市", "aliases": []},
    "6416": {"name": "瑞祺電通", "industry": "通訊", "market": "上市", "aliases": []},
    "6431": {"name": "光麗", "industry": "光電", "market": "上市", "aliases": []},
    "6443": {"name": "元晶", "industry": "光電", "market": "上市", "aliases": []},
    "6446": {"name": "藥華藥", "industry": "生技", "market": "上市", "aliases": []},
    "6451": {"name": "訊芯-KY", "industry": "半導體", "market": "上市", "aliases": []},
    "6456": {"name": "GIS-KY", "industry": "光電", "market": "上市", "aliases": []},
    "6469": {"name": "大樹", "industry": "貿易百貨", "market": "上櫃", "aliases": []},
    "6472": {"name": "保瑞", "industry": "生技", "market": "上櫃", "aliases": []},
    "6477": {"name": "安集", "industry": "光電", "market": "上市", "aliases": []},
    "6488": {
        "name": "環球晶",
        "industry": "半導體",
        "market": "上櫃",
        "aliases": ["GlobalWafers"],
    },
    "6491": {"name": "晶碩", "industry": "生技", "market": "上市", "aliases": []},
    "6505": {"name": "台塑化", "industry": "油電", "market": "上市", "aliases": []},
    "6515": {"name": "穎崴", "industry": "半導體", "market": "上市", "aliases": []},
    "6526": {"name": "達發", "industry": "半導體", "market": "上市", "aliases": []},
    "6531": {"name": "愛普", "industry": "半導體", "market": "上市", "aliases": []},
    "6533": {
        "name": "晶心科",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["Andes"],
    },
    "6541": {"name": "泰福-KY", "industry": "生技", "market": "上市", "aliases": []},
    "6550": {"name": "北極星藥業", "industry": "生技", "market": "上市", "aliases": []},
    "6552": {"name": "訊聯", "industry": "生技", "market": "上櫃", "aliases": []},
    "6560": {"name": "欣大健康", "industry": "生技", "market": "上櫃", "aliases": []},
    "6573": {"name": "虹揚-KY", "industry": "半導體", "market": "上市", "aliases": []},
    "6576": {"name": "逸達", "industry": "生技", "market": "上櫃", "aliases": []},
    "6581": {"name": "鋼聯", "industry": "鋼鐵", "market": "上市", "aliases": []},
    "6582": {"name": "申豐", "industry": "橡膠", "market": "上市", "aliases": []},
    "6591": {
        "name": "動力-KY",
        "industry": "電腦週邊",
        "market": "上市",
        "aliases": [],
    },
    "6592": {"name": "和潤企業", "industry": "金融", "market": "上市", "aliases": []},
    "6605": {"name": "帝寶", "industry": "汽車零件", "market": "上市", "aliases": []},
    "6625": {"name": "必應", "industry": "文創", "market": "上市", "aliases": []},
    "6640": {"name": "均華", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6641": {"name": "基士德-KY", "industry": "機械", "market": "上市", "aliases": []},
    "6669": {
        "name": "緯穎",
        "industry": "電腦週邊",
        "market": "上市",
        "aliases": ["Wiwynn"],
    },
    "6670": {"name": "復盛應用", "industry": "機械", "market": "上市", "aliases": []},
    "6671": {"name": "三能-KY", "industry": "機械", "market": "上市", "aliases": []},
    "6672": {
        "name": "騰輝電子",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "6679": {"name": "鈺太", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6689": {"name": "伊雲谷", "industry": "資訊服務", "market": "上市", "aliases": []},
    "6691": {"name": "洋基工程", "industry": "機電", "market": "上市", "aliases": []},
    "6698": {
        "name": "旭暉應材",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "6706": {"name": "惠特", "industry": "光電", "market": "上市", "aliases": []},
    "6712": {"name": "長聖", "industry": "生技", "market": "上櫃", "aliases": []},
    "6719": {"name": "力智", "industry": "半導體", "market": "上市", "aliases": []},
    "6721": {"name": "信實保全", "industry": "其他", "market": "上市", "aliases": []},
    "6732": {"name": "昇佳電子", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6735": {"name": "美達科技", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6741": {"name": "91APP", "industry": "資訊服務", "market": "上櫃", "aliases": []},
    "6742": {"name": "澤米", "industry": "光電", "market": "上市", "aliases": []},
    "6756": {"name": "威鋒電子", "industry": "半導體", "market": "上市", "aliases": []},
    "6768": {"name": "志強-KY", "industry": "鞋業", "market": "上市", "aliases": []},
    "6770": {
        "name": "力積電",
        "industry": "半導體",
        "market": "上市",
        "aliases": ["PSMC"],
    },
    "6771": {"name": "平和環保", "industry": "其他", "market": "上櫃", "aliases": []},
    "6776": {
        "name": "展碁國際",
        "industry": "電子通路",
        "market": "上市",
        "aliases": [],
    },
    "6781": {"name": "AES-KY", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "6782": {"name": "視陽", "industry": "生技", "market": "上市", "aliases": []},
    "6788": {"name": "華景電", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6789": {"name": "采鈺", "industry": "半導體", "market": "上市", "aliases": []},
    "6790": {"name": "永豐實", "industry": "造紙", "market": "上市", "aliases": []},
    "6792": {"name": "詠業", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6799": {"name": "來頡", "industry": "半導體", "market": "上市", "aliases": []},
    "6805": {
        "name": "富世達",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "6806": {"name": "森崴能源", "industry": "油電", "market": "上市", "aliases": []},
    "6807": {"name": "峰源-KY", "industry": "家具", "market": "上市", "aliases": []},
    "6821": {"name": "聯寶", "industry": "通訊", "market": "上市", "aliases": []},
    "6826": {"name": "和淞", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6830": {"name": "汎銓", "industry": "半導體", "market": "上市", "aliases": []},
    "6834": {
        "name": "天二科技",
        "industry": "電子零組件",
        "market": "上市",
        "aliases": [],
    },
    "6835": {"name": "圓裕", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6854": {"name": "創威", "industry": "通訊", "market": "上櫃", "aliases": []},
    "6861": {"name": "睿生光電", "industry": "光電", "market": "上市", "aliases": []},
    "6869": {"name": "雲豹能源", "industry": "油電", "market": "上市", "aliases": []},
    "6873": {"name": "泓德能源", "industry": "油電", "market": "上市", "aliases": []},
    "6877": {"name": "鏵友益", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6881": {"name": "潤德", "industry": "營建", "market": "上櫃", "aliases": []},
    "6899": {"name": "天勤光電", "industry": "光電", "market": "上市", "aliases": []},
    "6901": {"name": "鑽石投資", "industry": "金融", "market": "上市", "aliases": []},
    "6904": {"name": "伯鑫", "industry": "機械", "market": "上櫃", "aliases": []},
    "6906": {"name": "現觀科", "industry": "資訊服務", "market": "上市", "aliases": []},
    "6914": {
        "name": "阜爾運通",
        "industry": "資訊服務",
        "market": "上市",
        "aliases": [],
    },
    "6923": {"name": "中台", "industry": "其他", "market": "上櫃", "aliases": []},
    "6933": {
        "name": "AMAX-KY",
        "industry": "電腦週邊",
        "market": "上市",
        "aliases": [],
    },
    "6937": {"name": "天虹", "industry": "半導體", "market": "上市", "aliases": []},
    "6944": {"name": "兆聯實業", "industry": "其他", "market": "上櫃", "aliases": []},
    "8011": {"name": "台通", "industry": "通訊", "market": "上市", "aliases": []},
    "8016": {"name": "矽創", "industry": "半導體", "market": "上市", "aliases": []},
    "8028": {
        "name": "昇陽半導體",
        "industry": "半導體",
        "market": "上市",
        "aliases": [],
    },
    "8039": {"name": "台虹", "industry": "電子零組件", "market": "上市", "aliases": []},
    "8046": {"name": "南電", "industry": "電子零組件", "market": "上市", "aliases": []},
    "8069": {
        "name": "元太",
        "industry": "光電",
        "market": "上櫃",
        "aliases": ["E Ink"],
    },
    "8070": {"name": "長華", "industry": "半導體", "market": "上市", "aliases": []},
    "8072": {"name": "陞達科技", "industry": "半導體", "market": "上櫃", "aliases": []},
    "8081": {"name": "致新", "industry": "半導體", "market": "上市", "aliases": []},
    "8086": {"name": "宏捷科", "industry": "半導體", "market": "上櫃", "aliases": []},
    "8103": {"name": "瀚荃", "industry": "電子零組件", "market": "上櫃", "aliases": []},
    "8105": {"name": "凌巨", "industry": "光電", "market": "上市", "aliases": []},
    "8110": {"name": "華東", "industry": "半導體", "market": "上市", "aliases": []},
    "8112": {"name": "至上", "industry": "電子通路", "market": "上市", "aliases": []},
    "8150": {"name": "南茂", "industry": "半導體", "market": "上市", "aliases": []},
    "8155": {"name": "博智", "industry": "電子零組件", "market": "上櫃", "aliases": []},
    "8163": {"name": "達方", "industry": "電子零組件", "market": "上市", "aliases": []},
    "8201": {"name": "無敵", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "8210": {"name": "勤誠", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "8213": {"name": "志超", "industry": "電子零組件", "market": "上市", "aliases": []},
    "8215": {"name": "明基材", "industry": "光電", "market": "上市", "aliases": []},
    "8222": {"name": "寶一", "industry": "機械", "market": "上市", "aliases": []},
    "8249": {"name": "菱光", "industry": "電子零組件", "market": "上市", "aliases": []},
    "8255": {"name": "朋程", "industry": "汽車零件", "market": "上櫃", "aliases": []},
    "8261": {"name": "富鼎", "industry": "半導體", "market": "上市", "aliases": []},
    "8271": {"name": "宇瞻", "industry": "半導體", "market": "上市", "aliases": []},
    "8289": {"name": "泰藝", "industry": "電子零組件", "market": "上櫃", "aliases": []},
    "8299": {
        "name": "群聯",
        "industry": "半導體",
        "market": "上櫃",
        "aliases": ["Phison"],
    },
    "8341": {"name": "日友", "industry": "其他", "market": "上市", "aliases": []},
    "8374": {"name": "羅昇", "industry": "電子通路", "market": "上市", "aliases": []},
    "8404": {"name": "百和", "industry": "其他", "market": "上市", "aliases": []},
    "8411": {"name": "福貞-KY", "industry": "其他", "market": "上市", "aliases": []},
    "8422": {"name": "可寧衛", "industry": "其他", "market": "上市", "aliases": []},
    "8431": {"name": "匯鑽科", "industry": "其他", "market": "上櫃", "aliases": []},
    "8442": {"name": "威宏-KY", "industry": "鞋業", "market": "上市", "aliases": []},
    "8443": {"name": "阿瘦", "industry": "貿易百貨", "market": "上市", "aliases": []},
    "8454": {
        "name": "富邦媒",
        "industry": "貿易百貨",
        "market": "上市",
        "aliases": ["momo"],
    },
    "8462": {"name": "柏文", "industry": "運動", "market": "上市", "aliases": []},
    "8464": {"name": "億豐", "industry": "其他", "market": "上市", "aliases": []},
    "8466": {"name": "美吉吉-KY", "industry": "其他", "market": "上市", "aliases": []},
    "8467": {"name": "波力-KY", "industry": "運動", "market": "上市", "aliases": []},
    "8473": {"name": "山林水", "industry": "其他", "market": "上市", "aliases": []},
    "8476": {"name": "台境", "industry": "其他", "market": "上市", "aliases": []},
    "8481": {"name": "政伸", "industry": "其他", "market": "上市", "aliases": []},
    "8482": {"name": "商億-KY", "industry": "家具", "market": "上市", "aliases": []},
    "8488": {"name": "吉源-KY", "industry": "食品", "market": "上市", "aliases": []},
    "8499": {"name": "鼎炫-KY", "industry": "其他", "market": "上市", "aliases": []},
    "8926": {"name": "台汽電", "industry": "油電", "market": "上市", "aliases": []},
    "8936": {"name": "國統", "industry": "其他", "market": "上市", "aliases": []},
    "8940": {"name": "新天地", "industry": "觀光", "market": "上市", "aliases": []},
    "8996": {"name": "高力", "industry": "機械", "market": "上市", "aliases": []},
    "9802": {"name": "鈺齊-KY", "industry": "鞋業", "market": "上市", "aliases": []},
    "9904": {"name": "寶成", "industry": "鞋業", "market": "上市", "aliases": []},
    "9905": {"name": "大華", "industry": "其他", "market": "上市", "aliases": []},
    "9907": {"name": "統一實", "industry": "其他", "market": "上市", "aliases": []},
    "9910": {"name": "豐泰", "industry": "鞋業", "market": "上市", "aliases": []},
    "9911": {"name": "太子", "industry": "營建", "market": "上市", "aliases": []},
    "9914": {"name": "美利達", "industry": "運動", "market": "上市", "aliases": []},
    "9917": {"name": "中保科", "industry": "其他", "market": "上市", "aliases": []},
    "9918": {"name": "欣天然", "industry": "油電", "market": "上市", "aliases": []},
    "9921": {
        "name": "巨大",
        "industry": "運動",
        "market": "上市",
        "aliases": ["Giant"],
    },
    "9925": {"name": "新保", "industry": "其他", "market": "上市", "aliases": []},
    "9927": {"name": "泰銘", "industry": "其他", "market": "上市", "aliases": []},
    "9928": {"name": "中聯資源", "industry": "其他", "market": "上市", "aliases": []},
    "9930": {"name": "中聯資源", "industry": "其他", "market": "上市", "aliases": []},
    "9931": {"name": "欣高", "industry": "油電", "market": "上市", "aliases": []},
    "9933": {"name": "中鼎", "industry": "機電", "market": "上市", "aliases": []},
    "9934": {"name": "成霖", "industry": "其他", "market": "上市", "aliases": []},
    "9935": {"name": "慶豐富", "industry": "其他", "market": "上市", "aliases": []},
    "9937": {"name": "全國", "industry": "油電", "market": "上市", "aliases": []},
    "9938": {"name": "百和", "industry": "鞋業", "market": "上市", "aliases": []},
    "9940": {"name": "信義", "industry": "營建", "market": "上市", "aliases": []},
    "9941": {"name": "裕融", "industry": "金融", "market": "上市", "aliases": []},
    "9942": {"name": "潤泰新", "industry": "營建", "market": "上市", "aliases": []},
    "9943": {"name": "好樂迪", "industry": "觀光", "market": "上市", "aliases": []},
    "9944": {"name": "新麗", "industry": "其他", "market": "上市", "aliases": []},
    "9945": {"name": "潤泰新", "industry": "營建", "market": "上市", "aliases": []},
    "9946": {"name": "金麗-KY", "industry": "鞋業", "market": "上市", "aliases": []},
    "9955": {"name": "佳龍", "industry": "其他", "market": "上市", "aliases": []},
    "9958": {"name": "世紀鋼", "industry": "鋼鐵", "market": "上市", "aliases": []},
}

FALLBACK_STOCK_DB = {
    stock_id: {
        **info,
        "aliases": list(info.get("aliases", [])),
    }
    for stock_id, info in STOCK_DB.items()
}

INDUSTRY_CODES = {
    "01": "水泥",
    "02": "食品",
    "03": "塑膠",
    "04": "紡織纖維",
    "05": "電機機械",
    "06": "電器電纜",
    "07": "化學",
    "08": "玻璃陶瓷",
    "09": "造紙",
    "10": "鋼鐵",
    "11": "橡膠",
    "12": "汽車",
    "14": "建材營造",
    "15": "航運",
    "16": "觀光餐旅",
    "17": "金融保險",
    "18": "貿易百貨",
    "19": "綜合",
    "20": "其他",
    "21": "化學",
    "22": "生技醫療",
    "23": "油電燃氣",
    "24": "半導體",
    "25": "電腦及週邊設備",
    "26": "光電",
    "27": "通信網路",
    "28": "電子零組件",
    "29": "電子通路",
    "30": "資訊服務",
    "31": "其他電子",
    "32": "文化創意",
    "33": "農業科技",
    "34": "電子商務",
    "35": "綠能環保",
    "36": "數位雲端",
    "37": "運動休閒",
    "38": "居家生活",
}

NAME_TO_ID: Dict[str, str] = {}
STOCK_DB_SOURCE = "built_in_fallback"
STOCK_DB_STATUS = "fallback"
STOCK_DB_UPDATED_AT = ""
_STOCK_DB_LOADED = False


def _rebuild_name_index() -> None:
    NAME_TO_ID.clear()
    for stock_id, info in STOCK_DB.items():
        name = str(info["name"])
        NAME_TO_ID[name] = stock_id
        NAME_TO_ID[name.replace(" ", "")] = stock_id
        for alias in info.get("aliases", []):
            alias = str(alias)
            NAME_TO_ID[alias] = stock_id
            NAME_TO_ID[alias.replace(" ", "")] = stock_id


def _parse_int(value: Any) -> Optional[int]:
    try:
        text = str(value or "").replace(",", "").strip()
        return int(float(text)) if text else None
    except (TypeError, ValueError, OverflowError):
        return None


def _parse_tw_date(value: Any) -> str:
    """Convert YYYYMMDD or ROC YYYMMDD dates to ISO format."""
    text = re.sub(r"\D", "", str(value or ""))
    if len(text) == 7:
        year = int(text[:3]) + 1911
        month, day = int(text[3:5]), int(text[5:7])
    elif len(text) == 8:
        year, month, day = int(text[:4]), int(text[4:6]), int(text[6:8])
    else:
        return ""
    try:
        from datetime import date

        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def _company_asset_type(name: str, full_name: str) -> str:
    value = f"{name} {full_name}".upper()
    return "tdr" if "-DR" in value or "存託憑證" in value else "stock"


def _parse_official_rows(rows: Any, market: str) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    if market == "上市":
        source_name = "TWSE OpenAPI"
        official_url = TWSE_COMPANY_URL
    elif market == "興櫃":
        source_name = "TPEx OpenAPI"
        official_url = TPEX_EMERGING_URL
    else:
        source_name = "TPEx OpenAPI"
        official_url = TPEX_COMPANY_URL
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, dict):
            continue
        stock_id = str(
            row.get("SecuritiesCompanyCode") or row.get("公司代號") or ""
        ).strip()
        if not re.fullmatch(r"\d{4,6}", stock_id):
            continue
        name = (
            str(row.get("CompanyAbbreviation") or row.get("公司簡稱") or "")
            .strip()
            .rstrip("*")
            .strip()
        )
        if not name:
            continue
        code = (
            str(row.get("SecuritiesIndustryCode") or row.get("產業別") or "")
            .strip()
            .zfill(2)
        )
        fallback = FALLBACK_STOCK_DB.get(stock_id, {})
        aliases = list(fallback.get("aliases", []))
        full_name = str(row.get("CompanyName") or row.get("公司名稱") or "").strip()
        if full_name and full_name not in aliases and full_name != name:
            aliases.append(full_name)
        result[stock_id] = {
            "name": name,
            "industry": INDUSTRY_CODES.get(code, fallback.get("industry", "")),
            "industry_code": code,
            "market": market,
            "asset_type": _company_asset_type(name, full_name),
            "currency": "TWD",
            "listing_date": _parse_tw_date(
                row.get("上市日期") or row.get("上櫃日期") or row.get("DateOfListing")
            ),
            "paid_in_capital": _parse_int(
                row.get("實收資本額") or row.get("Paidin.Capital.NTDollars")
            ),
            "aliases": aliases,
            "source": source_name,
            "official_source": official_url,
            "source_updated_at": _parse_tw_date(row.get("出表日期") or row.get("Date")),
        }
    return result


def _parse_twse_fund_rows(rows: Any) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, dict):
            continue
        stock_id = str(row.get("基金代號") or "").strip().upper()
        if not re.fullmatch(r"[0-9A-Z]{4,6}", stock_id):
            continue
        name = str(row.get("基金簡稱") or "").strip()
        if not name:
            continue
        aliases = []
        for field in ("基金中文名稱", "基金英文名稱"):
            alias = str(row.get(field) or "").strip()
            if alias and alias != name and alias not in aliases:
                aliases.append(alias)
        result[stock_id] = {
            "name": name,
            "industry": "ETF",
            "market": "上市",
            "asset_type": "etf",
            "currency": "TWD",
            "listing_date": _parse_tw_date(row.get("上市日期")),
            "aliases": aliases,
            "fund_type": str(row.get("基金類型") or "").strip(),
            "tracking_index": str(row.get("標的指數/追蹤指數名稱") or "").strip(),
            "source": "TWSE OpenAPI",
            "official_source": TWSE_FUND_URL,
            "source_updated_at": _parse_tw_date(row.get("出表日期")),
        }
    return result


def _parse_tpex_etf_payload(payload: Any) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(payload, dict) or payload.get("stat") != "ok":
        return result
    tables = payload.get("tables")
    if not isinstance(tables, list) or not tables:
        return result
    table = tables[0]
    fields = table.get("fields", []) if isinstance(table, dict) else []
    rows = table.get("data", []) if isinstance(table, dict) else []
    if not isinstance(fields, list) or not isinstance(rows, list):
        return result
    indexes = {str(field).strip(): index for index, field in enumerate(fields)}
    code_index = indexes.get("證券代號")
    name_index = indexes.get("證券名稱")
    aum_index = indexes.get("基金規模(元)")
    if code_index is None or name_index is None:
        return result
    for row in rows:
        if not isinstance(row, list) or max(code_index, name_index) >= len(row):
            continue
        stock_id = str(row[code_index] or "").strip().upper()
        name = str(row[name_index] or "").strip()
        if not re.fullmatch(r"[0-9A-Z]{4,6}", stock_id) or not name:
            continue
        aum = (
            _parse_int(row[aum_index])
            if aum_index is not None and aum_index < len(row)
            else None
        )
        result[stock_id] = {
            "name": name,
            "industry": "ETF",
            "market": "上櫃",
            "asset_type": "etf",
            "currency": "TWD",
            "listing_date": "",
            "aliases": [],
            "aum": aum,
            "source_date": str(payload.get("date") or ""),
            "source": "TPEx official download",
            "official_source": TPEX_ETF_URL,
            "source_updated_at": _parse_tw_date(payload.get("date")),
        }
    return result


def _parse_twse_etn_payloads(
    payloads: Dict[str, Any], source_date: str = ""
) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    observed_at = source_date or datetime.now(TAIPEI_TIMEZONE).date().isoformat()
    for category, payload in payloads.items():
        if not isinstance(payload, dict) or payload.get("stat") != "ok":
            return {}
        fields = payload.get("fields")
        rows = payload.get("data")
        if not isinstance(fields, list) or not isinstance(rows, list):
            return {}
        indexes = {str(field).strip(): index for index, field in enumerate(fields)}
        code_index = indexes.get("證券代號")
        name_index = indexes.get("證券簡稱")
        if code_index is None or name_index is None:
            return {}
        for row in rows:
            if not isinstance(row, list) or max(code_index, name_index) >= len(row):
                continue
            stock_id = str(row[code_index] or "").strip().upper()
            name = str(row[name_index] or "").strip()
            if not re.fullmatch(r"02[0-9A-Z]{4}", stock_id) or not name:
                continue
            if stock_id in result:
                continue
            result[stock_id] = {
                "name": name,
                "industry": "ETN",
                "market": "上市",
                "asset_type": "etn",
                "currency": "TWD",
                "listing_date": "",
                "aliases": [],
                "etn_type": category,
                "source": "TWSE official product list",
                "official_source": TWSE_ETN_URLS[category],
                "source_updated_at": observed_at,
            }
    return result


def _supplemental_asset_type(
    stock_id: str, known_records: Dict[str, Dict[str, Any]]
) -> tuple[str, str]:
    if re.fullmatch(r"00[0-9A-Z]{4}", stock_id):
        return "etf", ""
    if re.fullmatch(r"02[0-9A-Z]{4}", stock_id):
        return "etn", ""
    if re.fullmatch(r"010\d{2}T", stock_id):
        return "reit", ""
    preferred = re.fullmatch(r"(\d{4})[A-Z](?:\d)?", stock_id)
    if preferred and preferred.group(1) in known_records:
        return "preferred_stock", preferred.group(1)
    return "", ""


def _parse_supplemental_security_rows(
    rows: Any,
    market: str,
    known_records: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(rows, list):
        return result
    if market == "上市":
        code_fields = ("Code", "證券代號")
        name_fields = ("Name", "證券名稱")
        official_url = TWSE_DAILY_SECURITIES_URL
        source_name = "TWSE OpenAPI daily securities"
    else:
        code_fields = ("SecuritiesCompanyCode", "證券代號")
        name_fields = ("CompanyName", "證券名稱")
        official_url = TPEX_DAILY_SECURITIES_URL
        source_name = "TPEx OpenAPI daily securities"
    for row in rows:
        if not isinstance(row, dict):
            continue
        stock_id = next(
            (
                str(row.get(field) or "").strip().upper()
                for field in code_fields
                if row.get(field)
            ),
            "",
        )
        if not stock_id or stock_id in known_records or stock_id in result:
            continue
        name = next(
            (
                str(row.get(field) or "").strip()
                for field in name_fields
                if row.get(field)
            ),
            "",
        )
        asset_type, issuer_stock_id = _supplemental_asset_type(stock_id, known_records)
        if not name or not asset_type:
            continue
        issuer = known_records.get(issuer_stock_id, {})
        industry = {"etf": "ETF", "etn": "ETN", "reit": "REIT"}.get(
            asset_type, issuer.get("industry", "")
        )
        record = {
            "name": name,
            "industry": industry,
            "market": market,
            "asset_type": asset_type,
            "currency": "TWD",
            "listing_date": "",
            "aliases": [],
            "source": source_name,
            "official_source": official_url,
            "source_updated_at": _parse_tw_date(row.get("Date")),
        }
        if issuer_stock_id:
            record["issuer_stock_id"] = issuer_stock_id
        if asset_type == "etf":
            record["fund_type"] = "daily_registry_fallback"
        result[stock_id] = record
    return result


def _fetch_stock_list_from_twse() -> Dict[str, Dict[str, Any]]:
    try:
        response = requests.get(
            TWSE_COMPANY_URL,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return _parse_official_rows(response.json(), "上市")
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("TWSE stock list fetch failed: %s", exc)
        return {}


def _fetch_tpex_stock_list() -> Dict[str, Dict[str, Any]]:
    try:
        response = requests.get(
            TPEX_COMPANY_URL,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return _parse_official_rows(response.json(), "上櫃")
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("TPEx stock list fetch failed: %s", exc)
        return {}


def _fetch_tpex_emerging_list() -> Dict[str, Dict[str, Any]]:
    try:
        response = requests.get(
            TPEX_EMERGING_URL,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return _parse_official_rows(response.json(), "興櫃")
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("TPEx emerging list fetch failed: %s", exc)
        return {}


def _fetch_twse_fund_list() -> Dict[str, Dict[str, Any]]:
    try:
        response = requests.get(
            TWSE_FUND_URL,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return _parse_twse_fund_rows(response.json())
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("TWSE fund list fetch failed: %s", exc)
        return {}


def _fetch_tpex_etf_list() -> Dict[str, Dict[str, Any]]:
    try:
        response = requests.post(
            TPEX_ETF_URL,
            headers=HEADERS,
            data={"response": "json"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return _parse_tpex_etf_payload(response.json())
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("TPEx ETF list fetch failed: %s", exc)
        return {}


def _fetch_twse_etn_list() -> Dict[str, Dict[str, Any]]:
    payloads: Dict[str, Any] = {}
    try:
        for category, url in TWSE_ETN_URLS.items():
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            payloads[category] = response.json()
        return _parse_twse_etn_payloads(payloads)
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("TWSE ETN list fetch failed: %s", exc)
        return {}


def _fetch_supplemental_security_list(
    market: str, known_records: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    url = TWSE_DAILY_SECURITIES_URL if market == "上市" else TPEX_DAILY_SECURITIES_URL
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        return _parse_supplemental_security_rows(response.json(), market, known_records)
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("%s supplemental security list fetch failed: %s", market, exc)
        return {}


def fetch_official_security_groups() -> Dict[str, Dict[str, Dict[str, Any]]]:
    listed = _fetch_stock_list_from_twse()
    otc = _fetch_tpex_stock_list()
    company_records = {**listed, **otc}

    emerging_raw = _fetch_tpex_emerging_list()
    emerging = {
        stock_id: record
        for stock_id, record in emerging_raw.items()
        if stock_id not in company_records
    }
    listed_funds = _fetch_twse_fund_list()
    otc_funds = _fetch_tpex_etf_list()
    listed_etns = _fetch_twse_etn_list()

    known_records = {
        **company_records,
        **emerging,
        **listed_funds,
        **otc_funds,
        **listed_etns,
    }
    listed_supplemental = _fetch_supplemental_security_list("上市", known_records)
    known_records.update(listed_supplemental)
    otc_supplemental = _fetch_supplemental_security_list("上櫃", known_records)
    return {
        "listed": listed,
        "otc": otc,
        "emerging": emerging,
        "listed_funds": listed_funds,
        "otc_funds": otc_funds,
        "listed_etns": listed_etns,
        "listed_supplemental": listed_supplemental,
        "otc_supplemental": otc_supplemental,
    }


def _load_official_snapshot() -> Dict[str, Dict[str, Any]]:
    snapshot_path = os.path.join(
        os.path.dirname(__file__), "official_stock_snapshot.json"
    )
    try:
        with open(snapshot_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        stocks = payload.get("stocks", {})
        return stocks if isinstance(stocks, dict) and len(stocks) >= 1500 else {}
    except (OSError, json.JSONDecodeError, AttributeError):
        return {}


def _load_official_snapshot_metadata() -> Dict[str, Any]:
    snapshot_path = os.path.join(
        os.path.dirname(__file__), "official_stock_snapshot.json"
    )
    try:
        with open(snapshot_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _validated_live_mapping(
    groups: Dict[str, Dict[str, Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    minimums = {
        "listed": 800,
        "otc": 700,
        "emerging": 250,
        "listed_funds": 200,
        "otc_funds": 80,
        "listed_etns": 5,
        "listed_supplemental": 20,
        "otc_supplemental": 5,
    }
    required = {
        "asset_type",
        "market",
        "currency",
        "listing_date",
        "official_source",
        "source_updated_at",
    }
    if any(len(groups.get(name, {})) < minimum for name, minimum in minimums.items()):
        return {}
    merged: Dict[str, Dict[str, Any]] = {}
    for records in groups.values():
        for stock_id, record in records.items():
            if stock_id in merged or not required <= set(record):
                return {}
            if not record.get("official_source") or not record.get("source_updated_at"):
                return {}
            merged[stock_id] = record
    return merged


def refresh_stock_db(force: bool = False) -> str:
    """Load a validated cache or tracked official snapshot; network refresh is explicit."""
    global _STOCK_DB_LOADED, STOCK_DB_SOURCE, STOCK_DB_STATUS, STOCK_DB_UPDATED_AT
    if _STOCK_DB_LOADED and not force:
        return STOCK_DB_SOURCE

    from utils.cache import cache_get, cache_set

    cached = (
        None
        if force
        else cache_get("official", "security_mapping_v7", max_age_sec=86400)
    )
    mapping: Dict[str, Dict[str, Any]] = {}
    if (
        isinstance(cached, dict)
        and isinstance(cached.get("stocks"), dict)
        and len(cached["stocks"]) >= 1500
    ):
        mapping = cached["stocks"]
        STOCK_DB_SOURCE = "official_cache"
        STOCK_DB_STATUS = "official"
        STOCK_DB_UPDATED_AT = str(cached.get("updated_at") or "")
    if force:
        mapping = _validated_live_mapping(fetch_official_security_groups())
        if mapping:
            updated_at = max(
                (record.get("source_updated_at", "") for record in mapping.values()),
                default="",
            )
            cache_set(
                "official",
                "security_mapping_v7",
                {
                    "stocks": mapping,
                    "updated_at": updated_at,
                },
            )
            cache_set(
                "official",
                "security_registry_attempt_v1",
                {
                    "status": "official",
                    "updated_at": updated_at,
                },
            )
            STOCK_DB_SOURCE = "official_live"
            STOCK_DB_STATUS = "official"
            STOCK_DB_UPDATED_AT = updated_at
        else:
            cache_set(
                "official",
                "security_registry_attempt_v1",
                {
                    "status": "stale",
                    "updated_at": "",
                },
            )
    if not mapping:
        mapping = _load_official_snapshot()
        if mapping:
            metadata = _load_official_snapshot_metadata()
            STOCK_DB_SOURCE = (
                "official_snapshot_stale" if force else "official_snapshot"
            )
            STOCK_DB_STATUS = "stale" if force else "official"
            STOCK_DB_UPDATED_AT = str(metadata.get("fetched_at") or "")

    if mapping:
        STOCK_DB.clear()
        STOCK_DB.update(mapping)
    else:
        STOCK_DB.clear()
        STOCK_DB.update(FALLBACK_STOCK_DB)
        STOCK_DB_SOURCE = "built_in_fallback"
        STOCK_DB_STATUS = "fallback"
        STOCK_DB_UPDATED_AT = ""
    _rebuild_name_index()
    _STOCK_DB_LOADED = True
    return STOCK_DB_SOURCE


def refresh_security_registry_if_due() -> str:
    """Perform at most one official registry refresh attempt per 24 hours."""
    from utils.cache import cache_get

    recent_attempt = cache_get(
        "official", "security_registry_attempt_v1", max_age_sec=86400
    )
    if recent_attempt is not None:
        return refresh_stock_db()
    return refresh_stock_db(force=True)


def normalize(query: str) -> Dict[str, Any]:
    refresh_stock_db()
    raw = str(query or "").strip()
    tokens = raw.split()
    code_candidate = tokens[0].upper() if tokens else ""
    if re.fullmatch(r"(?=.*\d)[0-9A-Z]{4,6}", code_candidate):
        stock_id = code_candidate
        if stock_id in STOCK_DB:
            info = STOCK_DB[stock_id].copy()
            info["stock_id"] = stock_id
            return info
        return {
            "stock_id": "",
            "name": raw,
            "industry": "",
            "market": "",
            "asset_type": "",
            "aliases": [],
        }

    normalized_query = raw.replace(" ", "")
    stock_id = NAME_TO_ID.get(normalized_query)
    if stock_id:
        info = STOCK_DB[stock_id].copy()
        info["stock_id"] = stock_id
        return info
    return {
        "stock_id": "",
        "name": normalized_query,
        "industry": "",
        "market": "",
        "asset_type": "",
        "aliases": [],
    }


def search_stock(query: str) -> List[Dict[str, Any]]:
    refresh_stock_db()
    value = str(query or "").strip()
    if not value:
        return []
    lower_query = value.lower()
    results = []
    for stock_id, info in STOCK_DB.items():
        aliases = info.get("aliases", [])
        haystacks = [stock_id, info["name"], *aliases]
        if any(lower_query in str(item).lower() for item in haystacks):
            result = info.copy()
            result["stock_id"] = stock_id
            results.append(result)
    results.sort(
        key=lambda item: (
            0
            if value in (item["stock_id"], item["name"])
            else 1
            if item["stock_id"].startswith(value) or item["name"].startswith(value)
            else 2,
            item["stock_id"],
        )
    )
    return results[:30]


_rebuild_name_index()
