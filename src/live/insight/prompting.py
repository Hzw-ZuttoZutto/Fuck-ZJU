from __future__ import annotations

from src.live.insight.models import KeywordConfig


def build_system_prompt() -> str:
    return (
        "你是课堂实时关键信息提取助手。"
        "请基于当前10秒转写文本和历史文本块上下文，判断是否有重要信息。"
        "输出必须是严格 JSON 对象，不得输出任何额外文本。"
        "JSON 字段必须包含："
        "important(boolean), summary(string), context_summary(string), "
        "matched_terms(string array), reason(string)。"
        "如果没有重要信息：important=false, summary='当前没有什么重要内容', "
        "context_summary='无重要内容'。"
        "不要输出逐字稿，不要复述过长原文，只输出概括性结论。"
    )


def build_user_prompt(
    *,
    keywords: KeywordConfig,
    current_text: str,
    context_text: str,
) -> str:
    return (
        "请结合以下规则分析：\n"
        f"{keywords.prompt_text()}\n"
        f"当前10秒转写文本：\n{current_text}\n"
        "历史文本块上下文（按时间顺序）：\n"
        f"{context_text}\n"
        "请返回严格 JSON。"
    )
