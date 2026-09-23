import json
import shutil

from core.config_loader import load_all_configs
from core.default_configs import DEFAULT_FILES, restore_default_configs, upgrade_outdated_configs
from tests.conftest import PROJECT_DIR


def test_embedded_defaults_match_configs_folder():
    for rel_path, content in DEFAULT_FILES.items():
        on_disk = (PROJECT_DIR / rel_path).read_text(encoding="utf-8").rstrip("\n")
        assert on_disk == content, f"{rel_path} changed; run python embed_default_configs.py"


def test_outdated_program_config_is_replaced_and_user_mapping_kept(tmp_path):
    shutil.copytree(PROJECT_DIR / "configs", tmp_path / "configs")

    aggregation = tmp_path / "configs" / "deklar-aggregation.json"
    old = json.loads(aggregation.read_text(encoding="utf-8"))
    old["config_version"] = 1
    old["field_rules"] = old["field_rules"][:1]
    aggregation.write_text(json.dumps(old), encoding="utf-8")

    mapping = tmp_path / "configs" / "mappings" / "tax-grid-mapping.json"
    edited = json.loads(mapping.read_text(encoding="utf-8"))
    edited["tags"]["77"] = {"targets": []}
    mapping.write_text(json.dumps(edited), encoding="utf-8")

    messages = upgrade_outdated_configs(str(tmp_path))

    assert len(messages) == 1 and "deklar-aggregation.json" in messages[0]
    assert (tmp_path / "configs" / "deklar-aggregation.json.v1.bak").exists()
    assert json.loads(aggregation.read_text(encoding="utf-8"))["config_version"] == 2
    assert "77" in json.loads(mapping.read_text(encoding="utf-8"))["tags"]
    load_all_configs(str(tmp_path / "configs"))


def test_restored_defaults_are_valid(tmp_path):
    restore_default_configs(str(tmp_path))
    load_all_configs(str(tmp_path / "configs"))
