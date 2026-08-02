"""플러그인 마켓플레이스 매니페스트를 검증한다.

매니페스트가 깨지면 `/plugin marketplace add` 가 실패하거나, 더 나쁘게는
설치는 되는데 스킬이 안 보인다. 경로가 실제로 존재하는지까지 확인한다.
"""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"

#: 공식 마켓플레이스에서 실제로 쓰이는 값들.
KNOWN_CATEGORIES = {
    "automation",
    "database",
    "deployment",
    "design",
    "development",
    "learning",
    "location",
    "math",
    "migration",
    "monitoring",
    "productivity",
    "security",
    "testing",
}


class ManifestFileTest(unittest.TestCase):
    def test_manifest_exists(self):
        self.assertTrue(
            MANIFEST_PATH.is_file(),
            ".claude-plugin/marketplace.json 이 없다",
        )

    def test_manifest_is_valid_json(self):
        try:
            json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.fail(f"marketplace.json 파싱 실패: {exc}")


class MarketplaceMetadataTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_marketplace_is_named(self):
        self.assertEqual(self.manifest.get("name"), "end-test")

    def test_owner_is_declared(self):
        owner = self.manifest.get("owner")
        self.assertIsInstance(owner, dict, "owner 블록이 없다")
        self.assertTrue(owner.get("name"), "owner.name 이 비었다")


class PluginEntryTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        plugins = self.manifest.get("plugins", [])
        self.assertEqual(len(plugins), 1, "플러그인 항목은 하나여야 한다")
        self.plugin = plugins[0]

    def test_plugin_is_named(self):
        self.assertEqual(self.plugin.get("name"), "end-test")

    def test_plugin_has_description(self):
        self.assertGreaterEqual(
            len(self.plugin.get("description", "")),
            40,
            "설치 목록에서 이 설명만 보고 고른다. 너무 짧다",
        )

    def test_category_is_known(self):
        self.assertIn(self.plugin.get("category"), KNOWN_CATEGORIES)

    def test_declared_skill_paths_exist(self):
        skills = self.plugin.get("skills", [])
        self.assertTrue(skills, "skills 배열이 비었다. 설치해도 아무것도 안 생긴다")
        for rel in skills:
            with self.subTest(skill=rel):
                skill_dir = (REPO_ROOT / rel).resolve()
                self.assertTrue(skill_dir.is_dir(), f"{rel} 디렉터리가 없다")
                self.assertTrue(
                    (skill_dir / "SKILL.md").is_file(),
                    f"{rel}/SKILL.md 이 없다",
                )

    def test_description_matches_skill_frontmatter(self):
        """매니페스트와 스킬 설명이 갈라지면 목록과 실물이 달라진다."""
        from test_skill_contract import read_skill, split_frontmatter

        fields, _ = split_frontmatter(read_skill())
        self.assertEqual(
            self.plugin.get("description"),
            fields.get("description"),
            "marketplace.json 의 description 이 SKILL.md 프론트매터와 다르다",
        )
