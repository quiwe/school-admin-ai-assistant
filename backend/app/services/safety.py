SENSITIVE_KEYWORDS = [
    "成绩",
    "绩点",
    "挂科",
    "处分",
    "退学",
    "休学",
    "学籍",
    "奖学金结果",
    "助学金结果",
    "名单",
    "投诉",
    "举报",
    "申诉",
    "心理危机",
    "自杀",
    "威胁",
    "隐私",
    "身份证",
    "手机号",
    "家庭情况",
]

HUMAN_REVIEW_TEMPLATE = (
    "同学你好，这个问题涉及个人情况或需要进一步核实，建议不要在群里公开发送个人信息。"
    "请将姓名、学号、专业及相关截图私发给负责老师，老师核实后再回复你。"
)


def detect_sensitive(question: str) -> tuple[bool, list[str]]:
    matched = [keyword for keyword in SENSITIVE_KEYWORDS if keyword in question]
    return bool(matched), matched
