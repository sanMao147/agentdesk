"""统一分词器（中英混合友好）。

中文分词策略：字符 + 字符 bigram（连续两个字符组合）
- "我爱北京天安门" → ["我", "爱", "北", "京", "天", "安", "门", "我爱", "爱北", "北京", "京天", "天安", "安门"]

英文/数字分词策略：空格分词
- "Hello World 123" → ["hello", "world", "123"]

统一分词器的好处：
- BM25 和离线 fallback embedding 共用，保证一致性
- 中文无空格，bigram 策略有效捕捉词语边界
- 零外部依赖，可离线运行
"""
from __future__ import annotations

import re
from typing import List

# 英文/数字词匹配正则
_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    """分词函数。

    处理流程：
    1. 转小写
    2. 提取英文/数字词（空格分词）
    3. 提取中文字符
    4. 生成中文字符 bigram

    Args:
        text: 输入文本

    Returns:
        分词结果列表
    """
    text = text.lower()

    # 英文/数字词
    words = _WORD.findall(text)

    # 中文字符
    cjk = [c for c in text if "一" <= c <= "鿿"]

    # 中文字符 bigram（连续两个字符组合）
    bigrams = [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]

    return words + cjk + bigrams
