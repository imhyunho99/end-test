"""코덱스용 포장을 검증한다.

SKILL.md 자체는 Claude Code와 코덱스가 같은 형식을 쓰므로 공유한다.
다른 것은 플러그인 매니페스트와 마켓플레이스뿐이라, 두 벌이 서로 어긋나지
않는지가 핵심이다. 코덱스가 번들한 공식 검증기가 있으면 그것도 돌린다.
"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CODEX_PLUGIN_PATH = REPO_ROOT / ".codex-plugin" / "plugin.json"
CODEX_MARKETPLACE_PATH = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
CLAUDE_MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"

OFFICIAL_VALIDATOR = (
    Path.home()
    / ".codex/skills/.system/plugin-creator/scripts/validate_plugin.py"
)

VALID_INSTALL_POLICIES = {"NOT_AVAILABLE", "AVAILABLE", "INSTALLED_BY_DEFAULT"}
VALID_AUTH_POLICIES = {"ON_INSTALL", "ON_USE"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CodexPluginManifestTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            CODEX_PLUGIN_PATH.is_file(), ".codex-plugin/plugin.json 이 없다"
        )
        self.manifest = load(CODEX_PLUGIN_PATH)

    def test_name_matches_skill(self):
        self.assertEqual(self.manifest.get("name"), "end-test")

    def test_license_is_declared(self):
        self.assertEqual(self.manifest.get("license"), "MIT")

    def test_skills_path_exists(self):
        rel = self.manifest.get("skills")
        self.assertTrue(rel, "skills 경로가 없다. 설치해도 아무것도 안 생긴다")
        self.assertTrue(rel.startswith("./"), "경로는 ./ 로 시작해야 한다")
        target = (REPO_ROOT / rel).resolve()
        self.assertTrue(target.is_dir(), f"{rel} 디렉터리가 없다")
        self.assertTrue(
            (target / "end-test" / "SKILL.md").is_file(),
            f"{rel} 아래에 end-test/SKILL.md 가 없다",
        )

    def test_description_matches_skill_frontmatter(self):
        from test_skill_contract import read_skill, split_frontmatter

        fields, _ = split_frontmatter(read_skill())
        self.assertEqual(
            self.manifest.get("description"),
            fields.get("description"),
            "plugin.json 의 description 이 SKILL.md 프론트매터와 다르다",
        )


class CodexMarketplaceTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            CODEX_MARKETPLACE_PATH.is_file(),
            ".agents/plugins/marketplace.json 이 없다",
        )
        self.manifest = load(CODEX_MARKETPLACE_PATH)
        plugins = self.manifest.get("plugins", [])
        self.assertEqual(len(plugins), 1, "플러그인 항목은 하나여야 한다")
        self.entry = plugins[0]

    def test_marketplace_is_named(self):
        self.assertTrue(self.manifest.get("name"), "마켓플레이스 name 이 비었다")

    def test_entry_name_matches_plugin(self):
        self.assertEqual(self.entry.get("name"), load(CODEX_PLUGIN_PATH)["name"])

    def test_source_resolves_to_plugin_root(self):
        source = self.entry.get("source", {})
        self.assertEqual(source.get("source"), "local")

        # 마켓플레이스 루트는 .agents/ 를 담은 디렉터리다.
        base = CODEX_MARKETPLACE_PATH.parent.parent.parent
        target = (base / source.get("path", "")).resolve()
        self.assertTrue(
            (target / ".codex-plugin" / "plugin.json").is_file(),
            f"source.path 가 plugin.json 이 있는 곳을 가리키지 않는다: {target}",
        )

    def test_policy_values_are_valid(self):
        policy = self.entry.get("policy", {})
        self.assertIn(policy.get("installation"), VALID_INSTALL_POLICIES)
        self.assertIn(policy.get("authentication"), VALID_AUTH_POLICIES)


class ManifestConsistencyTest(unittest.TestCase):
    """두 벌의 매니페스트가 갈라지면 진영마다 다른 물건이 설치된다."""

    def test_versions_agree(self):
        codex_version = load(CODEX_PLUGIN_PATH).get("version")
        claude_version = load(CLAUDE_MARKETPLACE_PATH)["metadata"]["version"]
        self.assertEqual(
            codex_version,
            claude_version,
            "코덱스 plugin.json 과 Claude marketplace.json 의 버전이 다르다",
        )


class OfficialValidatorTest(unittest.TestCase):
    def test_codex_validator_accepts_this_plugin(self):
        if not OFFICIAL_VALIDATOR.is_file():
            self.skipTest("코덱스 공식 검증기가 없는 환경")

        result = subprocess.run(
            ["python3", str(OFFICIAL_VALIDATOR), str(REPO_ROOT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"코덱스 검증기 실패:\n{result.stdout}\n{result.stderr}",
        )

    def test_codex_cli_is_available_for_manual_check(self):
        """CLI가 없으면 마켓플레이스 해석은 수동 확인이 불가능하다."""
        if shutil.which("codex") is None:
            self.skipTest("codex CLI 가 없는 환경")
