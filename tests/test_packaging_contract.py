from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_packaging_includes_runtime_assets_and_excludes_user_data():
    spec = (ROOT / "packaging" / "tw_stock_analysis.spec").read_text(encoding="utf-8")
    for required in (
        "fonts",
        "templates",
        "static",
        "picture",
        "official_stock_snapshot.json",
        "models/artifacts",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
    ):
        assert required in spec
    assert '("cache"' not in spec
    assert '("output"' not in spec
    assert "ROOT = Path(SPECPATH).resolve().parent" in spec
    assert "collect_all" not in spec
    assert "numpy.tests" in spec
    assert "pandas.tests" in spec


def test_packaged_smoke_mode_can_skip_opening_a_browser():
    source = (ROOT / "webui.py").read_text(encoding="utf-8")
    assert 'TWSTOCK_NO_BROWSER") == "1"' in source


def test_installer_prompts_before_removing_user_data():
    installer = (ROOT / "packaging" / "installer.iss").read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in installer
    assert "AppPublisher=胖貓貓工作室" in installer
    assert "LicenseFile=..\\LICENSE" in installer
    assert "FatCatGameStudio\\TWStockAnalysis" in installer
    assert "MB_YESNO" in installer
    assert "DelTree" in installer


def test_project_has_selected_mit_license():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("MIT License")
    assert "Copyright (c) 2026 胖貓貓工作室" in license_text


def test_build_script_generates_portable_hashes():
    script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")
    assert "PyInstaller" in script
    assert "Compress-Archive" in script
    assert "SHA256SUMS.txt" in script
    assert "Get-FileHash" in script
    assert "Programs\\Inno Setup 6\\ISCC.exe" in script
    assert "Inno Setup build 失敗" in script


def test_ci_audits_runtime_dependencies_and_checks_formatting():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "pip-audit==2.10.1" in requirements
    assert "python -m pip_audit -r requirements.txt" in workflow
    assert "python -m ruff format --check ." in workflow
