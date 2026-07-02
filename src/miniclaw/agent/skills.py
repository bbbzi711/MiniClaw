"""技能加载器 —— 发现、解析并加载 skills/ 目录下的技能定义。"""

import os

import yaml


class SkillsLoader:
    """扫描 skills_dir 下的子目录，解析 SKILL.md 的 frontmatter，提供技能列表和加载。

    使用示例::

        loader = SkillsLoader("skills")
        summary = loader.build_skills_summary()   # → 拼入 System Prompt
        content = loader.load_skill("my-skill")   # → 按需读取技能详细指南
    """

    def __init__(self, skills_dir: str = "skills") -> None:
        self.skills_dir = skills_dir

    # ---- 静态工具 ----

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[dict, str]:
        """解析 SKILL.md 的 YAML frontmatter。

        返回 (metadata字典, 去掉frontmatter后的正文)。
        无 frontmatter 时返回 (空字典, 原文)。
        """
        if not content.startswith("---\n"):
            return {}, content

        # 找到第二个 "---"
        end = content.find("\n---", 4)
        if end == -1:
            return {}, content

        yaml_block = content[4:end]
        try:
            metadata = yaml.safe_load(yaml_block) or {}
        except yaml.YAMLError:
            metadata = {}

        body = content[end + 4:].lstrip("\n")
        return metadata, body

    # ---- 内部辅助 ----

    def _discover_skills(self) -> list[dict]:
        """扫描 skills_dir，返回 [{name, description, path, rel_path}, ...] 列表。"""
        skills: list[dict] = []

        if not os.path.isdir(self.skills_dir):
            return skills

        for entry in sorted(os.listdir(self.skills_dir)):
            skill_dir = os.path.join(self.skills_dir, entry)
            if not os.path.isdir(skill_dir):
                continue

            skill_md = os.path.join(skill_dir, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue

            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue

            metadata, _body = self._parse_frontmatter(content)
            rel_path = os.path.relpath(skill_md)

            skills.append({
                "name": metadata.get("name", entry),
                "description": metadata.get("description", ""),
                "path": skill_md,
                "rel_path": rel_path,
            })

        return skills

    # ---- 公共方法 ----

    def build_skills_summary(self) -> str:
        """构建可用技能摘要，用于拼接到 System Prompt 中。

        如果 skills_dir 不存在或无任何技能，返回空字符串。
        """
        skills = self._discover_skills()
        if not skills:
            return ""

        lines = [
            "你有以下技能可用。当你需要使用某项技能时，",
            "请先用 read_file 工具读取对应的 SKILL.md 文件获取详细指南。",
            "",
            "可用技能：",
        ]

        for s in skills:
            name = s["name"]
            rel_path = s["rel_path"]
            desc = s["description"]
            lines.append(f"- {name} ({rel_path})：{desc}")

        return "\n".join(lines)

    def load_skill(self, name: str) -> str | None:
        """加载指定名称的技能正文（去掉 frontmatter 后的内容）。

        找不到对应 SKILL.md 时返回 None。
        """
        if not os.path.isdir(self.skills_dir):
            return None

        skill_md = os.path.join(self.skills_dir, name, "SKILL.md")
        if not os.path.isfile(skill_md):
            return None

        try:
            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return None

        _metadata, body = self._parse_frontmatter(content)
        return body

    def list_skills(self) -> list[dict]:
        """返回所有已发现技能列表，用于调试和管理。"""
        return self._discover_skills()
