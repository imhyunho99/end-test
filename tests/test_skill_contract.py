"""SKILL.md가 설계 문서에서 정한 계약을 지키는지 검증한다.

스킬은 에이전트가 읽는 지시서라 실행 결과를 단위 테스트할 수 없다.
대신 지시서가 갖춰야 할 계약 — 프론트매터, 채점 규칙, 로그 경로,
공개 안전성 — 을 검증한다. 이것들은 문서를 손볼 때 조용히 깨진다.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "skills" / "end-test" / "SKILL.md"


def read_skill() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """--- 로 감싼 프론트매터를 얕게 파싱한다. 값은 전부 문자열."""
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.DOTALL)
    if not match:
        raise AssertionError("프론트매터 블록(--- ... ---)이 없다")

    fields = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, match.group(2)


class SkillFileTest(unittest.TestCase):
    def test_skill_file_exists(self):
        self.assertTrue(
            SKILL_PATH.is_file(),
            f"{SKILL_PATH.relative_to(REPO_ROOT)} 가 없다",
        )


class FrontmatterTest(unittest.TestCase):
    def setUp(self):
        self.fields, _ = split_frontmatter(read_skill())

    def test_name_matches_directory(self):
        self.assertEqual(self.fields.get("name"), "end-test")

    def test_description_states_when_to_use(self):
        """description은 스킬 목록에서 호출 판단의 유일한 근거다."""
        description = self.fields.get("description", "")
        self.assertGreaterEqual(len(description), 40, "description이 너무 짧다")
        self.assertIn("end-test", description)


class InvocationTest(unittest.TestCase):
    def setUp(self):
        _, self.body = split_frontmatter(read_skill())

    def test_default_question_count_is_five(self):
        self.assertRegex(
            self.body,
            r"기본[^\n]*5문항|5문항[^\n]*기본",
            "기본 문항 수가 5라는 규정이 없다",
        )

    def test_question_count_is_overridable_by_argument(self):
        self.assertRegex(
            self.body,
            r"/end-test\s+\d",
            "인자로 문항 수를 바꾸는 사용법이 없다",
        )


class QuestionSourceTest(unittest.TestCase):
    def setUp(self):
        _, self.body = split_frontmatter(read_skill())

    def test_all_four_axes_are_named(self):
        for axis in ["설계 판단", "엣지케이스", "CS 기본기", "그냥 넘어간 지점"]:
            with self.subTest(axis=axis):
                self.assertIn(axis, self.body, f"출제 축 '{axis}' 가 없다")

    def test_blind_spot_axis_has_detection_criteria(self):
        """'그냥 넘어간 지점'은 판정이 모호해서 기준이 없으면 작동하지 않는다."""
        self.assertRegex(
            self.body,
            r"되묻지 않|승인만|묻지 않",
            "blind spot 판정 기준이 없다",
        )

    def test_blind_spot_axis_is_prioritized(self):
        self.assertRegex(
            self.body,
            r"그냥 넘어간 지점[^\n]*우선|우선[^\n]*그냥 넘어간 지점",
            "'그냥 넘어간 지점'을 우선한다는 규정이 없다",
        )

    def test_questions_are_open_ended(self):
        self.assertRegex(
            self.body,
            r"객관식[^\n]*(않|말|금지)",
            "서술형만 낸다는 규정이 없다",
        )


class GradingTest(unittest.TestCase):
    def setUp(self):
        _, self.body = split_frontmatter(read_skill())

    def test_three_grades_exist(self):
        for grade in ["○", "△", "✗"]:
            with self.subTest(grade=grade):
                self.assertIn(grade, self.body, f"판정 기호 '{grade}' 가 없다")

    def test_grading_criterion_is_explainability(self):
        """정답 여부가 아니라 설명 가능성으로 판정한다."""
        self.assertRegex(
            self.body,
            r"설명할 수 있는가|설명 가능",
            "채점 기준이 '설명할 수 있는가'로 명시되지 않았다",
        )

    def test_forbids_lenient_grading(self):
        """채점이 후해지면 도구 전체가 무의미해진다. 가장 중요한 계약."""
        self.assertRegex(
            self.body,
            r"△.{0,20}○.{0,30}(올리지|주지) (말|않)|후하게",
            "후한 채점을 금지하는 지시가 없다",
        )

    def test_partial_grade_is_not_recorded(self):
        self.assertRegex(
            self.body,
            r"△[^\n]*기록(하지|은)? ?(않|말)",
            "△를 기록하지 않는다는 규정이 없다",
        )


class WrongAnswerTest(unittest.TestCase):
    def setUp(self):
        _, self.body = split_frontmatter(read_skill())

    def test_wrong_answer_triggers_immediate_requestion(self):
        self.assertRegex(
            self.body,
            r"즉시 재질문|바로 재질문",
            "✗ 즉시 재질문 규정이 없다",
        )

    def test_requestion_changes_angle(self):
        """방금 들은 설명을 되뇌면 맞힐 수 있는 재질문은 검증이 안 된다."""
        self.assertRegex(
            self.body,
            r"각도를 바꾸|다른 상황",
            "재질문이 각도를 바꿔야 한다는 규정이 없다",
        )

    def test_requestion_does_not_consume_question_budget(self):
        self.assertRegex(
            self.body,
            r"재질문[^\n]*문항 수에 (포함하지|넣지) ?않",
            "재질문을 문항 수에서 제외한다는 규정이 없다",
        )


class RecordTest(unittest.TestCase):
    def setUp(self):
        _, self.body = split_frontmatter(read_skill())

    def test_log_path_is_exact(self):
        self.assertIn("~/.claude/end-test/YYYY-MM-DD.md", self.body)

    def test_log_is_outside_repo(self):
        """공개 레포에 학습 이력이 들어가면 안 된다."""
        self.assertRegex(
            self.body,
            r"레포 (밖|외부)|저장소 밖",
            "로그가 레포 밖이라는 규정이 없다",
        )

    def test_record_fields_are_specified(self):
        for field in ["주제", "무엇을 몰랐는가", "해결"]:
            with self.subTest(field=field):
                self.assertIn(field, self.body, f"기록 항목 '{field}' 가 없다")


class PublicationSafetyTest(unittest.TestCase):
    """MIT로 공개하는 레포다. 사적인 것도 남의 것도 들어가면 안 된다."""

    #: 스킬 예시를 쓰다 보면 실제 업무 맥락이 딸려 들어오기 쉽다.
    #: 새 프로젝트를 맡으면 여기에 추가한다.
    PRIVATE_IDENTIFIERS = [
        "docenty",
        "cofathon",
        "올리브영",
        "크래프톤",
        "woomi",
        "alphadata",
        "alphamodels",
        "nahyeonho",
        "nahyunho",
        "imhyunho99",
    ]

    def setUp(self):
        self.raw = read_skill()

    def offending_lines(self, predicate) -> list[str]:
        """위반한 줄만 돌려준다. 파일 전체를 실패 메시지에 쏟지 않기 위해."""
        return [line for line in self.raw.splitlines() if predicate(line)]

    def test_no_private_identifiers(self):
        for token in self.PRIVATE_IDENTIFIERS:
            with self.subTest(token=token):
                hits = self.offending_lines(lambda line: token in line.lower())
                self.assertEqual(hits, [], f"사적 식별자 '{token}' 가 들어있다")

    def test_no_absolute_home_paths(self):
        pattern = re.compile(r"/Users/[A-Za-z0-9._-]+")
        hits = self.offending_lines(pattern.search)
        self.assertEqual(hits, [], "특정 사용자 홈 경로가 박혀 있다. ~ 로 쓴다")

    def test_no_verbatim_lines_from_installed_skills(self):
        """설치된 다른 스킬의 문장을 옮기면 그쪽 라이선스가 따라온다."""
        search_roots = [
            Path.home() / ".claude" / "skills",
            Path.home() / ".claude" / "plugins",
        ]
        existing = [root for root in search_roots if root.is_dir()]
        if not existing:
            self.skipTest("비교할 설치된 스킬이 없는 환경")

        mine = {
            line.strip()
            for line in self.raw.splitlines()
            if len(line.strip()) >= 40
        }
        self.assertTrue(mine, "비교할 만큼 긴 줄이 없다")

        for root in existing:
            for other in root.rglob("*.md"):
                # 플러그인으로 설치하면 이 스킬의 사본이 ~/.claude/plugins 아래
                # 놓인다. 자기 사본을 표절로 잡지 않도록 걸러낸다.
                if "end-test" in other.parts:
                    continue
                try:
                    text = other.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                overlap = mine & {
                    line.strip()
                    for line in text.splitlines()
                    if len(line.strip()) >= 40
                }
                self.assertFalse(
                    overlap,
                    f"{other} 와 같은 문장이 있다: {sorted(overlap)[:2]}",
                )


class SummaryTest(unittest.TestCase):
    def setUp(self):
        _, self.body = split_frontmatter(read_skill())

    def test_no_score_or_grade(self):
        """숫자는 학습 신호를 가린다."""
        self.assertRegex(
            self.body,
            r"(점수|등급)[^\n]*(매기지|않는다|말)",
            "점수·등급을 매기지 않는다는 규정이 없다",
        )
