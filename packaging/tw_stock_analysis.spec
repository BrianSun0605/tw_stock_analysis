# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


ROOT = Path(SPECPATH).resolve().parent


datas = [
    (str(ROOT / "fonts"), "fonts"),
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "static"), "static"),
    (str(ROOT / "picture"), "picture"),
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "stock" / "official_stock_snapshot.json"), "stock"),
    (str(ROOT / "models" / "artifacts"), "models/artifacts"),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    (str(ROOT / "docs" / "PRIVACY.md"), "docs"),
    (str(ROOT / "docs" / "UI_DESIGN_SYSTEM.md"), "docs"),
]
binaries = []
hiddenimports = collect_submodules(
    "yfinance",
    filter=lambda name: ".tests" not in name and ".test" not in name,
)
datas += collect_data_files("yfinance", excludes=["**/tests/**"])
datas += copy_metadata("yfinance")

a = Analysis(
    [str(ROOT / "webui.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "pytest",
        "playwright",
        "numpy.tests",
        "pandas.tests",
        "matplotlib.tests",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TWStockAnalysis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="TWStockAnalysis",
)
