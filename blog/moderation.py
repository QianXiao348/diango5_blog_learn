import os
import re
import json
from typing import Tuple

from django.conf import settings
import onnxruntime
from transformers import AutoTokenizer
import numpy as np
import torch
import torch.nn.functional as F


# 词典文件
SENSITIVE_WORDS_FILE_PATH = getattr(settings, 'SENSITIVE_WORDS_FILE', None)
SENSITIVE_WORDS = set()  # 敏感词词典

# 模型文件和分词器路径
ONNX_MODEL_PATH = os.path.join(getattr(settings, 'BASE_DIR'), 'sjt_blog', 'model', 'insult_model.onnx')
TOKENIZER_DIR = os.path.join(getattr(settings, 'BASE_DIR'), 'sjt_blog', 'model')

onnx_session = None  # 加载和推理 ONNX 模型的会话对象
tokenizer = None  # 将输入的文本数据转化为适合模型的输入格式
ADVANCED_LABELS = ["正常", "违规"]

def load_advanced_model():
    """
    加载ONNX模型和分词器
    """
    global onnx_session, tokenizer
    try:
        if os.path.exists(ONNX_MODEL_PATH) and os.path.exists(TOKENIZER_DIR):
            onnx_session = onnxruntime.InferenceSession(ONNX_MODEL_PATH)  # 加载和运行ONNX模型
            tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_DIR)  # 预训练语言模型的分词器
            print("Successfully loaded ONNX model and tokenizer for advanced moderation.")
        else:
            print("警告：未找到ONNX模型或分词器。高级审查将不生效!")
    except Exception as e:
        print(f"ERROR: Failed to load ONNX model or tokenizer: {e}")
        onnx_session = None
        tokenizer = None

# 在应用启动时加载模型
load_advanced_model()

#  构建词典字典树
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False


def build_trie(sensitive_words):
    """
    根据敏感词列表构建字典树
    """
    root = TrieNode()
    for word in sensitive_words:
        node = root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
    return root


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
TRIE_ROOT = build_trie(SENSITIVE_WORDS)  # 构建字典树

# 初级审查：正则表达式规则
REGEX_RULES = [
    (re.compile(r'(.)\1{6,}'), "包含了过多的重复字符。"),
    (re.compile(r'http[s]?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:\S*)'), "包含了外部链接。"),
]

def moderate_content(text: str) -> Tuple[bool, str]:
    """
    内容审查主函数，负责调用各级审查策略。
    返回 (is_safe, message)。
    Args:
        text (str): 用户输入的文本。
    Returns:
        tuple: (True, "合规") 如果内容规范；(False, "违规") 如果内容不规范。
    """

    # 1. 初级审查（规则匹配）
    is_safe, message = primary_moderation(text)
    if not is_safe:
        return False, message

    # 2. 高级审查（机器学习） - 待实现
    is_safe, message = advanced_moderation(text)
    if not is_safe:
        return False, message
    #
    # # 3. 第三方API接口集成 - 待实现
    # is_safe, message = third_party_api_moderation(text)
    # if not is_safe:
    #     return False, message

    # 如果通过所有检查，则认为规范
    return True, "内容合规"


def primary_moderation(text: str) -> Tuple[bool, str]:
    """
    初级审查，基于敏感词和正则表达式进行匹配。
    """
    text_lower = text.lower()
    # 遍历文本，从每个字符开始尝试匹配敏感词
    for i in range(len(text_lower)):
        node = TRIE_ROOT
        j = i
        while j < len(text_lower) and text_lower[j] in node.children:
            node = node.children[text_lower[j]]
            if node.is_end:
                # 找到敏感词，返回匹配的词语
                matched_word = text_lower[i:j + 1]
                print(f"contains sensitive word: {matched_word}")
                return False, f"文字含有敏感词：{matched_word}"
            j += 1

    for regex, message in REGEX_RULES:
        if regex.search(text):
            return False, message

    return True, "内容合规"


def advanced_moderation(text: str) -> Tuple[bool, str]:
    """
    高级审查，基于深度学习模型进行判断。
    """
    if not onnx_session or not tokenizer:
        return True, ""  # 如果模型未加载，则默认安全

    try:
        # 对输入文本进行编码和预处理
        encoding = tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=256,
            padding='max_length',
            truncation=True,
            return_tensors='np'  # onnxruntime 需要numpy数组
        )

        # 准备模型输入
        onnx_inputs = {
            'input_ids': encoding['input_ids'].astype(np.int64),
            'attention_mask': encoding['attention_mask'].astype(np.int64)
        }

        # 执行推理
        outputs = onnx_session.run(None, onnx_inputs)
        logits = outputs[0]

        # 将logits转换为概率，并判断结果
        probabilities = F.softmax(torch.tensor(logits), dim=1)
        prob_normal = probabilities[0][0].item()
        prob_violation = probabilities[0][1].item()
        print(f'advanced moderation -> prob_normal: {prob_normal:.3f}, prob_violation: {prob_violation:.3f}')

        threshold = 0.55
        if prob_violation >= threshold:
            return False, f"内容违规（模型置信度：{prob_violation:.2f}）"

        return True, ""

    except Exception as e:
        print(f"Error during ONNX model prediction: {e}")
        return True, ""  # 如果预测失败，则默认安全
