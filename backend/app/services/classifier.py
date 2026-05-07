from .safety import detect_sensitive


CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("论文答辩类", ["论文", "答辩", "盲审", "开题", "查重", "导师"]),
    ("系统类", ["系统", "登录", "上传", "审核", "账号", "密码", "截图", "网页"]),
    ("时间类", ["截止", "什么时候", "几号", "时间", "期限", "多久"]),
    ("材料类", ["材料", "证明", "附件", "表格", "申请表", "盖章"]),
    ("学籍类", ["学籍", "休学", "复学", "退学", "转专业", "保留入学资格"]),
    ("奖助学金类", ["奖学金", "助学金", "资助", "困难认定", "补助"]),
    ("个人隐私类", ["身份证", "手机号", "家庭情况", "隐私", "姓名", "学号"]),
    ("投诉申诉类", ["投诉", "举报", "申诉", "不公平"]),
    ("流程类", ["流程", "办理", "怎么弄", "怎么申请", "步骤", "手续"]),
]


def classify_question(question: str) -> str:
    sensitive, keywords = detect_sensitive(question)
    if sensitive:
        if any(word in keywords for word in ["投诉", "举报", "申诉"]):
            return "投诉申诉类"
        if any(word in keywords for word in ["身份证", "手机号", "家庭情况", "隐私"]):
            return "个人隐私类"
        if any(word in keywords for word in ["学籍", "退学", "休学"]):
            return "学籍类"
        if any(word in keywords for word in ["奖学金结果", "助学金结果"]):
            return "奖助学金类"

    scores: dict[str, int] = {}
    for category, keywords_for_category in CATEGORY_RULES:
        scores[category] = sum(1 for keyword in keywords_for_category if keyword in question)
    best_category, best_score = max(scores.items(), key=lambda item: item[1])
    return best_category if best_score > 0 else "其他"
