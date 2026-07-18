import json
import os
import re
from typing import Any, Dict, List, Optional
import requests
from config import CACHE_DIR, HEADERS, TIMEOUT
from utils.logger import get_logger

logger = get_logger(__name__)

STOCK_DB = {
    "1101": {"name": "台泥", "industry": "水泥", "market": "上市", "aliases": ["Taiwan Cement"]},
    "1102": {"name": "亞泥", "industry": "水泥", "market": "上市", "aliases": []},
    "1201": {"name": "味全", "industry": "食品", "market": "上市", "aliases": []},
    "1210": {"name": "大成", "industry": "食品", "market": "上市", "aliases": []},
    "1216": {"name": "統一", "industry": "食品", "market": "上市", "aliases": ["Uni-President"]},
    "1301": {"name": "台塑", "industry": "塑膠", "market": "上市", "aliases": ["Formosa Plastics"]},
    "1303": {"name": "南亞", "industry": "塑膠", "market": "上市", "aliases": ["Nan Ya"]},
    "1326": {"name": "台化", "industry": "塑膠", "market": "上市", "aliases": ["Formosa Chemicals"]},
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
    "2002": {"name": "中鋼", "industry": "鋼鐵", "market": "上市", "aliases": ["China Steel"]},
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
    "2301": {"name": "光寶科", "industry": "電子零組件", "market": "上市", "aliases": ["Lite-On"]},
    "2303": {"name": "聯電", "industry": "半導體", "market": "上市", "aliases": ["UMC"]},
    "2308": {"name": "台達電", "industry": "電子零組件", "market": "上市", "aliases": ["Delta Electronics"]},
    "2317": {"name": "鴻海", "industry": "電子代工", "market": "上市", "aliases": ["Hon Hai", "Foxconn"]},
    "2324": {"name": "仁寶", "industry": "電子代工", "market": "上市", "aliases": ["Compal"]},
    "2327": {"name": "國巨", "industry": "電子零組件", "market": "上市", "aliases": ["Yageo"]},
    "2330": {"name": "台積電", "industry": "半導體", "market": "上市", "aliases": ["TSMC", "台GG"]},
    "2331": {"name": "精英", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "2347": {"name": "聯強", "industry": "電子通路", "market": "上市", "aliases": ["Synnex"]},
    "2353": {"name": "宏碁", "industry": "電腦週邊", "market": "上市", "aliases": ["Acer"]},
    "2354": {"name": "鴻準", "industry": "電子零組件", "market": "上市", "aliases": []},
    "2356": {"name": "英業達", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "2357": {"name": "華碩", "industry": "電腦週邊", "market": "上市", "aliases": ["ASUS"]},
    "2360": {"name": "致茂", "industry": "電子測試", "market": "上市", "aliases": []},
    "2376": {"name": "技嘉", "industry": "電腦週邊", "market": "上市", "aliases": ["Gigabyte"]},
    "2377": {"name": "微星", "industry": "電腦週邊", "market": "上市", "aliases": ["MSI"]},
    "2379": {"name": "瑞昱", "industry": "半導體", "market": "上市", "aliases": ["Realtek"]},
    "2382": {"name": "廣達", "industry": "電腦週邊", "market": "上市", "aliases": ["Quanta"]},
    "2383": {"name": "台光電", "industry": "電子零組件", "market": "上市", "aliases": []},
    "2385": {"name": "群光", "industry": "電子零組件", "market": "上市", "aliases": []},
    "2395": {"name": "研華", "industry": "工業電腦", "market": "上市", "aliases": ["Advantech"]},
    "2408": {"name": "南亞科", "industry": "半導體", "market": "上市", "aliases": ["Nanya Tech"]},
    "2409": {"name": "友達", "industry": "面板", "market": "上市", "aliases": ["AUO"]},
    "2412": {"name": "中華電", "industry": "電信", "market": "上市", "aliases": ["CHT"]},
    "2449": {"name": "京元電子", "industry": "半導體", "market": "上市", "aliases": []},
    "2454": {"name": "聯發科", "industry": "半導體", "market": "上市", "aliases": ["MediaTek", "MTK"]},
    "2458": {"name": "義隆", "industry": "半導體", "market": "上市", "aliases": []},
    "2474": {"name": "可成", "industry": "電子零組件", "market": "上市", "aliases": []},
    "2481": {"name": "強茂", "industry": "半導體", "market": "上市", "aliases": []},
    "2492": {"name": "華新科", "industry": "電子零組件", "market": "上市", "aliases": []},
    "2498": {"name": "宏達電", "industry": "手機", "market": "上市", "aliases": ["HTC"]},
    "2501": {"name": "國建", "industry": "營建", "market": "上市", "aliases": []},
    "2548": {"name": "華固", "industry": "營建", "market": "上市", "aliases": []},
    "2603": {"name": "長榮", "industry": "航運", "market": "上市", "aliases": ["Evergreen"]},
    "2609": {"name": "陽明", "industry": "航運", "market": "上市", "aliases": ["Yang Ming"]},
    "2615": {"name": "萬海", "industry": "航運", "market": "上市", "aliases": ["Wan Hai"]},
    "2618": {"name": "長榮航", "industry": "航運", "market": "上市", "aliases": ["EVA Air"]},
    "2633": {"name": "台灣高鐵", "industry": "航運", "market": "上市", "aliases": []},
    "2801": {"name": "彰銀", "industry": "金融", "market": "上市", "aliases": []},
    "2809": {"name": "京城銀行", "industry": "金融", "market": "上市", "aliases": []},
    "2812": {"name": "台中銀行", "industry": "金融", "market": "上市", "aliases": []},
    "2823": {"name": "中壽", "industry": "金融", "market": "上市", "aliases": []},
    "2834": {"name": "臺企銀", "industry": "金融", "market": "上市", "aliases": []},
    "2880": {"name": "華南金", "industry": "金融", "market": "上市", "aliases": []},
    "2881": {"name": "富邦金", "industry": "金融", "market": "上市", "aliases": ["Fubon"]},
    "2882": {"name": "國泰金", "industry": "金融", "market": "上市", "aliases": ["Cathay"]},
    "2883": {"name": "開發金", "industry": "金融", "market": "上市", "aliases": []},
    "2884": {"name": "玉山金", "industry": "金融", "market": "上市", "aliases": []},
    "2885": {"name": "元大金", "industry": "金融", "market": "上市", "aliases": []},
    "2886": {"name": "兆豐金", "industry": "金融", "market": "上市", "aliases": []},
    "2887": {"name": "台新金", "industry": "金融", "market": "上市", "aliases": []},
    "2888": {"name": "新光金", "industry": "金融", "market": "上市", "aliases": []},
    "2890": {"name": "永豐金", "industry": "金融", "market": "上市", "aliases": []},
    "2891": {"name": "中信金", "industry": "金融", "market": "上市", "aliases": ["CTBC"]},
    "2892": {"name": "第一金", "industry": "金融", "market": "上市", "aliases": []},
    "2903": {"name": "遠百", "industry": "貿易百貨", "market": "上市", "aliases": []},
    "2912": {"name": "統一超", "industry": "貿易百貨", "market": "上市", "aliases": ["7-Eleven"]},
    "3005": {"name": "神基", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "3008": {"name": "大立光", "industry": "光電", "market": "上市", "aliases": ["Largan"]},
    "3017": {"name": "奇鋐", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3019": {"name": "亞光", "industry": "光電", "market": "上市", "aliases": []},
    "3023": {"name": "信邦", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3026": {"name": "禾伸堂", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3029": {"name": "零壹", "industry": "資訊服務", "market": "上市", "aliases": []},
    "3034": {"name": "聯詠", "industry": "半導體", "market": "上市", "aliases": ["Novatek"]},
    "3036": {"name": "文曄", "industry": "電子通路", "market": "上市", "aliases": []},
    "3037": {"name": "欣興", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3044": {"name": "健鼎", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3045": {"name": "台灣大", "industry": "電信", "market": "上市", "aliases": ["Taiwan Mobile"]},
    "3048": {"name": "益登", "industry": "電子通路", "market": "上市", "aliases": []},
    "3050": {"name": "鈺德", "industry": "光電", "market": "上市", "aliases": []},
    "3057": {"name": "喬鼎", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "3060": {"name": "銘異", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "3090": {"name": "日電貿", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3189": {"name": "景碩", "industry": "半導體", "market": "上市", "aliases": []},
    "3209": {"name": "全科", "industry": "電子通路", "market": "上市", "aliases": []},
    "3229": {"name": "晟鈦", "industry": "電子零組件", "market": "上市", "aliases": []},
    "3231": {"name": "緯創", "industry": "電腦週邊", "market": "上市", "aliases": ["Wistron"]},
    "3260": {"name": "威剛", "industry": "半導體", "market": "上市", "aliases": []},
    "3406": {"name": "玉晶光", "industry": "光電", "market": "上市", "aliases": []},
    "3413": {"name": "京鼎", "industry": "半導體", "market": "上市", "aliases": []},
    "3443": {"name": "創意", "industry": "半導體", "market": "上市", "aliases": ["Global Unichip"]},
    "3450": {"name": "聯鈞", "industry": "半導體", "market": "上市", "aliases": []},
    "3454": {"name": "晶睿", "industry": "光電", "market": "上市", "aliases": []},
    "3481": {"name": "群創", "industry": "面板", "market": "上市", "aliases": ["Innolux"]},
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
    "3661": {"name": "世芯-KY", "industry": "半導體", "market": "上市", "aliases": ["Alchip"]},
    "3673": {"name": "TPK-KY", "industry": "光電", "market": "上市", "aliases": []},
    "3686": {"name": "達能", "industry": "半導體", "market": "上市", "aliases": []},
    "3694": {"name": "海華", "industry": "通訊", "market": "上市", "aliases": []},
    "3702": {"name": "大聯大", "industry": "電子通路", "market": "上市", "aliases": ["WPG"]},
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
    "4904": {"name": "遠傳", "industry": "電信", "market": "上市", "aliases": ["Far EasTone"]},
    "4915": {"name": "致伸", "industry": "電子零組件", "market": "上市", "aliases": []},
    "4927": {"name": "泰鼎-KY", "industry": "電子零組件", "market": "上市", "aliases": []},
    "4938": {"name": "和碩", "industry": "電子代工", "market": "上市", "aliases": ["Pegatron"]},
    "4958": {"name": "臻鼎-KY", "industry": "電子零組件", "market": "上市", "aliases": []},
    "4966": {"name": "譜瑞-KY", "industry": "半導體", "market": "上櫃", "aliases": ["Parade"]},
    "4977": {"name": "眾達-KY", "industry": "通訊", "market": "上市", "aliases": []},
    "4986": {"name": "耕進", "industry": "電子零組件", "market": "上市", "aliases": []},
    "4994": {"name": "傳奇", "industry": "遊戲", "market": "上櫃", "aliases": []},
    "5007": {"name": "三星科技", "industry": "鋼鐵", "market": "上市", "aliases": []},
    "5203": {"name": "訊連", "industry": "資訊服務", "market": "上市", "aliases": []},
    "5269": {"name": "祥碩", "industry": "半導體", "market": "上市", "aliases": []},
    "5274": {"name": "信驊", "industry": "半導體", "market": "上櫃", "aliases": []},
    "5285": {"name": "界霖", "industry": "半導體", "market": "上市", "aliases": []},
    "5288": {"name": "豐祥-KY", "industry": "汽車零件", "market": "上市", "aliases": []},
    "5299": {"name": "杰力", "industry": "半導體", "market": "上櫃", "aliases": []},
    "5306": {"name": "訊連", "industry": "資訊服務", "market": "上櫃", "aliases": []},
    "5347": {"name": "世界", "industry": "半導體", "market": "上櫃", "aliases": ["Vanguard"]},
    "5371": {"name": "中光電", "industry": "光電", "market": "上櫃", "aliases": []},
    "5425": {"name": "台半", "industry": "半導體", "market": "上櫃", "aliases": []},
    "5434": {"name": "崇越", "industry": "電子通路", "market": "上櫃", "aliases": []},
    "5469": {"name": "瀚宇博", "industry": "電子零組件", "market": "上市", "aliases": []},
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
    "5906": {"name": "台南-KY", "industry": "貿易百貨", "market": "上櫃", "aliases": []},
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
    "6191": {"name": "精成科", "industry": "電子零組件", "market": "上市", "aliases": []},
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
    "6278": {"name": "台表科", "industry": "電子零組件", "market": "上市", "aliases": []},
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
    "6488": {"name": "環球晶", "industry": "半導體", "market": "上櫃", "aliases": ["GlobalWafers"]},
    "6491": {"name": "晶碩", "industry": "生技", "market": "上市", "aliases": []},
    "6505": {"name": "台塑化", "industry": "油電", "market": "上市", "aliases": []},
    "6515": {"name": "穎崴", "industry": "半導體", "market": "上市", "aliases": []},
    "6526": {"name": "達發", "industry": "半導體", "market": "上市", "aliases": []},
    "6531": {"name": "愛普", "industry": "半導體", "market": "上市", "aliases": []},
    "6533": {"name": "晶心科", "industry": "半導體", "market": "上市", "aliases": ["Andes"]},
    "6541": {"name": "泰福-KY", "industry": "生技", "market": "上市", "aliases": []},
    "6550": {"name": "北極星藥業", "industry": "生技", "market": "上市", "aliases": []},
    "6552": {"name": "訊聯", "industry": "生技", "market": "上櫃", "aliases": []},
    "6560": {"name": "欣大健康", "industry": "生技", "market": "上櫃", "aliases": []},
    "6573": {"name": "虹揚-KY", "industry": "半導體", "market": "上市", "aliases": []},
    "6576": {"name": "逸達", "industry": "生技", "market": "上櫃", "aliases": []},
    "6581": {"name": "鋼聯", "industry": "鋼鐵", "market": "上市", "aliases": []},
    "6582": {"name": "申豐", "industry": "橡膠", "market": "上市", "aliases": []},
    "6591": {"name": "動力-KY", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "6592": {"name": "和潤企業", "industry": "金融", "market": "上市", "aliases": []},
    "6605": {"name": "帝寶", "industry": "汽車零件", "market": "上市", "aliases": []},
    "6625": {"name": "必應", "industry": "文創", "market": "上市", "aliases": []},
    "6640": {"name": "均華", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6641": {"name": "基士德-KY", "industry": "機械", "market": "上市", "aliases": []},
    "6669": {"name": "緯穎", "industry": "電腦週邊", "market": "上市", "aliases": ["Wiwynn"]},
    "6670": {"name": "復盛應用", "industry": "機械", "market": "上市", "aliases": []},
    "6671": {"name": "三能-KY", "industry": "機械", "market": "上市", "aliases": []},
    "6672": {"name": "騰輝電子", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6679": {"name": "鈺太", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6689": {"name": "伊雲谷", "industry": "資訊服務", "market": "上市", "aliases": []},
    "6691": {"name": "洋基工程", "industry": "機電", "market": "上市", "aliases": []},
    "6698": {"name": "旭暉應材", "industry": "電子零組件", "market": "上市", "aliases": []},
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
    "6770": {"name": "力積電", "industry": "半導體", "market": "上市", "aliases": ["PSMC"]},
    "6771": {"name": "平和環保", "industry": "其他", "market": "上櫃", "aliases": []},
    "6776": {"name": "展碁國際", "industry": "電子通路", "market": "上市", "aliases": []},
    "6781": {"name": "AES-KY", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "6782": {"name": "視陽", "industry": "生技", "market": "上市", "aliases": []},
    "6788": {"name": "華景電", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6789": {"name": "采鈺", "industry": "半導體", "market": "上市", "aliases": []},
    "6790": {"name": "永豐實", "industry": "造紙", "market": "上市", "aliases": []},
    "6792": {"name": "詠業", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6799": {"name": "來頡", "industry": "半導體", "market": "上市", "aliases": []},
    "6805": {"name": "富世達", "industry": "電子零組件", "market": "上市", "aliases": []},
    "6806": {"name": "森崴能源", "industry": "油電", "market": "上市", "aliases": []},
    "6807": {"name": "峰源-KY", "industry": "家具", "market": "上市", "aliases": []},
    "6821": {"name": "聯寶", "industry": "通訊", "market": "上市", "aliases": []},
    "6826": {"name": "和淞", "industry": "半導體", "market": "上櫃", "aliases": []},
    "6830": {"name": "汎銓", "industry": "半導體", "market": "上市", "aliases": []},
    "6834": {"name": "天二科技", "industry": "電子零組件", "market": "上市", "aliases": []},
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
    "6914": {"name": "阜爾運通", "industry": "資訊服務", "market": "上市", "aliases": []},
    "6923": {"name": "中台", "industry": "其他", "market": "上櫃", "aliases": []},
    "6933": {"name": "AMAX-KY", "industry": "電腦週邊", "market": "上市", "aliases": []},
    "6937": {"name": "天虹", "industry": "半導體", "market": "上市", "aliases": []},
    "6944": {"name": "兆聯實業", "industry": "其他", "market": "上櫃", "aliases": []},
    "8011": {"name": "台通", "industry": "通訊", "market": "上市", "aliases": []},
    "8016": {"name": "矽創", "industry": "半導體", "market": "上市", "aliases": []},
    "8028": {"name": "昇陽半導體", "industry": "半導體", "market": "上市", "aliases": []},
    "8039": {"name": "台虹", "industry": "電子零組件", "market": "上市", "aliases": []},
    "8046": {"name": "南電", "industry": "電子零組件", "market": "上市", "aliases": []},
    "8069": {"name": "元太", "industry": "光電", "market": "上櫃", "aliases": ["E Ink"]},
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
    "8299": {"name": "群聯", "industry": "半導體", "market": "上櫃", "aliases": ["Phison"]},
    "8341": {"name": "日友", "industry": "其他", "market": "上市", "aliases": []},
    "8374": {"name": "羅昇", "industry": "電子通路", "market": "上市", "aliases": []},
    "8404": {"name": "百和", "industry": "其他", "market": "上市", "aliases": []},
    "8411": {"name": "福貞-KY", "industry": "其他", "market": "上市", "aliases": []},
    "8422": {"name": "可寧衛", "industry": "其他", "market": "上市", "aliases": []},
    "8431": {"name": "匯鑽科", "industry": "其他", "market": "上櫃", "aliases": []},
    "8442": {"name": "威宏-KY", "industry": "鞋業", "market": "上市", "aliases": []},
    "8443": {"name": "阿瘦", "industry": "貿易百貨", "market": "上市", "aliases": []},
    "8454": {"name": "富邦媒", "industry": "貿易百貨", "market": "上市", "aliases": ["momo"]},
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
    "9921": {"name": "巨大", "industry": "運動", "market": "上市", "aliases": ["Giant"]},
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

CACHE_FILE = os.path.join(CACHE_DIR, "stock_mapping.json")

NAME_TO_ID = {}
for sid, info in STOCK_DB.items():
    NAME_TO_ID[info["name"]] = sid
    for alias in info.get("aliases", []):
        NAME_TO_ID[alias] = sid


def _fetch_stock_list_from_twse() -> Optional[Any]:
    try:
        resp = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/TWTB4U",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException as e:
        logger.warning("TWSE stock list fetch failed: %s", e)
    return None


def _fetch_tpex_stock_list() -> Optional[Any]:
    try:
        url = "https://www.tpex.org.tw/openapi/v1/mopsfinmindqry"
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException as e:
        logger.warning("TPEx stock list fetch failed: %s", e)
    return None


def normalize(query: str) -> Dict[str, Any]:
    raw = query.strip()
    # 支援「2330 台積電」這種空白分隔的查詢 — 第一個 token 如果是數字就當 stock_id
    tokens = raw.split()
    if tokens and tokens[0].isdigit():
        stock_id = tokens[0]
        if stock_id in STOCK_DB:
            info = STOCK_DB[stock_id].copy()
            info["stock_id"] = stock_id
            return info
        name = raw[len(stock_id):].strip() or tokens[1] if len(tokens) > 1 else stock_id
        return {"stock_id": stock_id, "name": name, "industry": "", "market": "", "aliases": []}
    query = raw.replace(" ", "")
    if query.isdigit():
        stock_id = query
        if stock_id in STOCK_DB:
            info = STOCK_DB[stock_id].copy()
            info["stock_id"] = stock_id
            return info
        return {"stock_id": stock_id, "name": query, "industry": "", "market": "", "aliases": []}
    stock_id = NAME_TO_ID.get(query)
    if stock_id:
        info = STOCK_DB[stock_id].copy()
        info["stock_id"] = stock_id
        return info
    return {"stock_id": "", "name": query, "industry": "", "market": "", "aliases": []}


def search_stock(query: str) -> List[Dict[str, Any]]:
    results = []
    lower_query = query.lower()
    for sid, info in STOCK_DB.items():
        if query == sid or query == info["name"]:
            r = info.copy()
            r["stock_id"] = sid
            return [r]
    for sid, info in STOCK_DB.items():
        if query in sid or query in info["name"] or any(query in a for a in info.get("aliases", [])):
            r = info.copy()
            r["stock_id"] = sid
            if r not in results:
                results.append(r)
    for sid, info in STOCK_DB.items():
        if lower_query in info["name"].lower():
            if not any(r["stock_id"] == sid for r in results):
                r = info.copy()
                r["stock_id"] = sid
                results.append(r)
    results.sort(key=lambda x: (
        0 if query == x["stock_id"] or query == x["name"]
        else 1 if x["stock_id"].startswith(query) or x["name"].startswith(query)
        else 2
    ))
    return results
