from typing import Tuple, List
from pathlib import Path
import os
import re
from django.conf import settings

# 检查 settings.py 中是否定义了敏感词文件路径
SENSITIVE_WORDS_FILE_PATH = getattr(settings, 'SENSITIVE_WORDS_FILE', None)
SENSITIVE_WORDS = set()


def load_sensitive_words():
    """
    从文件中加载敏感词词典。
    在应用启动时调用。
    """
    global SENSITIVE_WORDS
    SENSITIVE_WORDS.clear()

    if not SENSITIVE_WORDS_FILE_PATH or not os.path.exists(SENSITIVE_WORDS_FILE_PATH):
        print("警告：未找到敏感词文件。内容审核将不太有效!")
        return

    try:
        with open(SENSITIVE_WORDS_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
            words = {line.strip().lower() for line in f if line.strip() and len(line.strip()) > 1}
            SENSITIVE_WORDS.update(words)
        print(f"Successfully loaded {len(SENSITIVE_WORDS)} sensitive words.")
    except Exception as e:
        print(f"ERROR: Failed to load sensitive words file: {e}")
        SENSITIVE_WORDS.clear()


load_sensitive_words()  # 应用启动时加载敏感词
# 初级审查：正则表达式规则
REGEX_RULES = [
    (re.compile(r'(.)\1{5,}'), "包含了过多的重复字符。"),
    (re.compile(r'http[s]?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:\S*)'), "包含了外部链接。"),
]

def moderate_content(text: str) -> Tuple[bool, str]:
    """
    内容审查主函数，负责调用各级审查策略。
    返回 (is_safe, message)。
    Args:
        text (str): 用户输入的文本。
    Returns:
        tuple: (True, "") 如果内容规范；(False, "原因") 如果内容不规范。
    """

    # 1. 初级审查（规则匹配）
    is_safe, message = primary_moderation(text)
    if not is_safe:
        return False, message

    # # 2. 高级审查（机器学习） - 待实现
    # is_safe, message = advanced_moderation(text)
    # if not is_safe:
    #     return False, message
    #
    # # 3. 第三方API接口集成 - 待实现
    # is_safe, message = third_party_api_moderation(text)
    # if not is_safe:
    #     return False, message

    # 如果通过所有检查，则认为规范
    return True, ""


def primary_moderation(text: str) -> Tuple[bool, str]:
    """
    初级审查，基于敏感词和正则表达式进行匹配。
    """
    text_lower = text.lower()
    for word in SENSITIVE_WORDS:
        if word in text_lower:
            print(f"contains sensitive word: {word}")
            return False, f"文字含有敏感词：{word}"

    for regex, message in REGEX_RULES:
        if regex.search(text):
            return False, message

    return True, ""

def advanced_moderation(text: str) -> Tuple[bool, str]:
    pass


def third_party_api_moderation(text: str) -> Tuple[bool, str]:
    pass
