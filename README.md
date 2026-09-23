# ov-19

REMEMBER TO ALWAYS RE-EMBED MODIFIED CONFIGS IN ORDER TO SHIP WITH DIST
python embed_default_configs.py
When a program-owned config (deklar-aggregation, schemas) changes, bump its config_version
and SUPPORTED_CONFIG_VERSIONS in core/config_loader.py, so installed copies are upgraded.

Setup: pip install -r requirements.txt   (the design spec is in SPEC.txt)
Tests: pytest   (optional real-data tests: set VATTOOL_FIXTURES, see tests/test_real_fixtures.py)
pyinstaller .\vattool_19.spec --clean
For distribution zip dist\VATTool_19\
Do not run from Program Files! 