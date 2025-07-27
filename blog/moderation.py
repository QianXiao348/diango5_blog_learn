from typing import Tuple

def moderate_comment_content(text: str) -> Tuple[bool, str]:
    """
    模拟本地模型对评论内容进行规范判断。
    返回 (is_safe, message)。

    Args:
        text (str): 用户输入的评论内容。

    Returns:
        tuple: (True, "") 如果内容规范；(False, "原因") 如果内容不规范。
    """
    # 示例规则：
    # 1. 如果包含敏感词
    sensitive_words = ["敏感词A", "暴力", "色情", "辱骂"]
    for word in sensitive_words:
        if word in text.lower(): # 转换为小写进行匹配
            return False, f"评论中包含不规范词语：'{word}'"

    
    # 你可以在这里集成更复杂的本地模型判断
    # 假设你有一个加载好的模型 model_pipeline = load_my_local_model()
    # prediction = model_pipeline.predict([text])[0]
    # if prediction == 'unsafe':
    #     return False, "您的评论被系统判定为不规范内容。"

    # 如果通过所有检查，则认为规范
    return (True,"")
