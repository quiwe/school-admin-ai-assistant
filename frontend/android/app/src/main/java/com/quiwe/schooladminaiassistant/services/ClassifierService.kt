package com.quiwe.schooladminaiassistant.services

object ClassifierService {
    private val CATEGORY_RULES = listOf(
        "论文答辩类" to listOf("论文", "答辩", "盲审", "开题", "查重", "导师"),
        "系统类" to listOf("系统", "登录", "上传", "审核", "账号", "密码", "截图", "网页"),
        "时间类" to listOf("截止", "什么时候", "几号", "时间", "期限", "多久"),
        "材料类" to listOf("材料", "证明", "附件", "表格", "申请表", "盖章"),
        "学籍类" to listOf("学籍", "休学", "复学", "退学", "转专业", "保留入学资格"),
        "奖助学金类" to listOf("奖学金", "助学金", "资助", "困难认定", "补助"),
        "个人隐私类" to listOf("身份证", "手机号", "家庭情况", "隐私", "姓名", "学号"),
        "投诉申诉类" to listOf("投诉", "举报", "申诉", "不公平"),
        "流程类" to listOf("流程", "办理", "怎么弄", "怎么申请", "步骤", "手续")
    )

    fun classify(question: String): String {
        val (sensitive, keywords) = SafetyService.detect(question)
        if (sensitive) {
            if (keywords.any { it in listOf("投诉", "举报", "申诉") }) return "投诉申诉类"
            if (keywords.any { it in listOf("身份证", "手机号", "家庭情况", "隐私") }) return "个人隐私类"
            if (keywords.any { it in listOf("学籍", "退学", "休学") }) return "学籍类"
            if (keywords.any { it in listOf("奖学金结果", "助学金结果") }) return "奖助学金类"
        }

        val scores = CATEGORY_RULES.map { (category, keywords) ->
            category to keywords.count { it in question }
        }
        val best = scores.maxByOrNull { it.second } ?: return "其他"
        return if (best.second > 0) best.first else "其他"
    }
}
