"""训练 CLI 的历史化叙事脚本层。

说明：
1. 重大历史节点、时间线和训练主题遵循抗战史实背景。
2. 具体人物、对白和现场细节属于艺术化二次改编，用于增强训练沉浸感。
3. 整体表达坚持人民立场、实事求是、积极向上的红色叙事基调。
"""

from __future__ import annotations

from typing import Any, Dict, List


# 史实场景对应的剧本配置放在模块级常量中，便于后续继续扩展为更多章节。
SCENE_STORY_LIBRARY: Dict[str, Dict[str, Any]] = {
    "S1": {
        "paragraphs": [
            "历史锚点：1937 年 7 月 7 日，卢沟桥事变爆发，中华民族全面抗战由此揭开悲壮序幕。",
            "{location}一带夜色未尽，断续枪声已经逼近城门。报馆里煤油灯摇晃，电话、电报、口述消息同时涌来，真假混杂。",
            "{player_name}第一次以{player_identity}的身份站到时代风口。你很快就会明白，第一条快讯争的不只是速度，更是在为人民守住第一道事实关口。",
            "本回任务是：{mission}。这一回真正要练的，不只是下笔快，而是在“{decision_focus}”上把分寸稳住。",
        ],
        "dialogues": [
            {
                "speaker": "陈编辑",
                "text": "{player_name}，枪声刚起，越不能让谣言跑在真相前面。记住，先写人民安危，再写稿件速度。",
            },
            {
                "speaker": "老通讯员赵川",
                "text": "前线消息再乱，我们的心不能乱。你把第一稿写稳，城里百姓就能少一分慌。",
            },
        ],
    },
    "S2": {
        "paragraphs": [
            "历史锚点：1937 年 8 月，淞沪会战打响。战况激烈、信息来源繁杂，记者面对的是更高强度的连续核验压力。",
            "北平的稿件刚刚见报，新的电报已经把你带到{location}。前线消息、租界传闻、街头议论交错在一起，任何一个数字失真，都会迅速放大群众焦虑。",
            "你开始懂得，真正有力量的战地报道，不是把最耸动的词写得最大，而是把最可信的事实送到人民面前。",
            "本回任务是：{mission}。采写时要特别注意“{decision_focus}”，让群众看到真相，也看到秩序和希望。",
        ],
        "dialogues": [
            {
                "speaker": "摄影员林岚",
                "text": "大家最怕听见半真半假的消息。你稿子里每少一分煽动，街头就多一分安定。",
            },
            {
                "speaker": "陈编辑",
                "text": "伤亡数字慢半拍不可怕，可怕的是错一拍。事实站稳了，士气才站得稳。",
            },
        ],
    },
    "S3": {
        "paragraphs": [
            "历史锚点：1937 年冬，南京失守后，大量幸存者、线人和普通群众都处在极端危险之中。",
            "战火之下，{location}不断有人从生死边缘退下来。有人愿意把看见的暴行告诉你，却也把最后一丝活路托付到你的笔下。",
            "这一回，你面对的不是简单的新闻技巧题，而是人民立场的底线题。真正的勇敢，不是把秘密写出去，而是让真相被看见、让活着的人继续活下去。",
            "本回任务是：{mission}。要守住“{decision_focus}”这条线，既不粉饰真相，也不拿幸存者去换所谓的证据感。",
        ],
        "dialogues": [
            {
                "speaker": "幸存者",
                "text": "记者同志，事情你可以写，请不要把我们的名字和藏身处写出去。活下来的人，还得继续活。",
            },
            {
                "speaker": "陈编辑",
                "text": "保护一个线人，不只是保护一个人，更是在保护后来者继续把真相送出来的可能。",
            },
        ],
    },
    "S4": {
        "paragraphs": [
            "历史锚点：1938 年，武汉会战期间，前线与后方同时承受巨大压力。报道既要告知，也要动员与引导。",
            "一路从前线写到后方，你看到的不只是炮火，还有群众如何在困难中组织起来、互相扶持。现在，{location}最需要的是清楚、可执行、能稳人心的沟通。",
            "你开始真正理解，红色新闻工作的力量，不只是记录苦难，更是帮助人民在苦难中找到方向、组织行动、守住信心。",
            "本回任务是：{mission}。这一次要把“{decision_focus}”落到具体语言上，让群众听得懂、做得到、愿意跟着做。",
        ],
        "dialogues": [
            {
                "speaker": "基层干部",
                "text": "老百姓不是不愿意行动，是怕听不懂、也怕走错路。你写得越清楚，大家越能稳住阵脚。",
            },
            {
                "speaker": "陈编辑",
                "text": "稳人心，不等于轻描淡写；讲危险，也不等于制造恐慌。你的笔，要把方向写出来。",
            },
        ],
    },
    "S5": {
        "paragraphs": [
            "历史锚点：1940 年百团大战期间，多路战况并进，电文、口述、民间线索同时涌来，核验链条更加复杂。",
            "到了{location}，你已经不再是刚入局时只想着抢发快讯的新人。真正的难题，变成了怎样在胜势中保持克制，在捷报中继续把核验链拉直。",
            "这是一场能力上的拔高训练：哪些能发，哪些待证，哪些即使轰动也必须压住不发。成熟记者的硬功夫，往往就在这种分层判断里。",
            "本回任务是：{mission}。你要围绕“{decision_focus}”给编辑部一个清清楚楚、经得起追问的发稿建议。",
        ],
        "dialogues": [
            {
                "speaker": "通讯员小韩",
                "text": "每一路都说自己的消息最准，可真正负责任的人，得先替编辑部把关，把人民的信任守住。",
            },
            {
                "speaker": "陈编辑",
                "text": "捷报可以鼓舞人，但不能掺水。越是振奋的时候，越要让核验链像钢轨一样笔直。",
            },
        ],
    },
    "S6": {
        "paragraphs": [
            "历史锚点：1945 年 8 月，日本宣布无条件投降。胜利消息振奋全国，也对重大节点报道提出了更高要求。",
            "{location}里灯火通明，纸张、铅字和电文堆满案头。所有人都知道，这一稿写出去，不只是告知消息，更是在记录民族解放战争的重要时刻。",
            "从 1937 到 1945，你已经在风雨里走过一整条成长线。此刻考验你的，不只是会不会写，而是能不能在万众期待中仍然守住边界、守住真实、守住人民信任。",
            "本回任务是：{mission}。最后一关，要在“{decision_focus}”上给出成熟答卷，让胜利的消息既振奋人心，也经得起历史追问。",
        ],
        "dialogues": [
            {
                "speaker": "陈编辑",
                "text": "{player_name}，越接近胜利时刻，越要让每一个字经得起后人追问。历史会记住这一天，也会记住我们怎样写下这一天。",
            },
            {
                "speaker": "印刷工老何",
                "text": "这一夜，大家都在盼着黎明。你把稿子写稳了，百姓看到的就不只是消息，还有信心。",
            },
        ],
    },
}


# 转场也做成配置，保证六个节点能被串成一条完整成长主线。
TRANSITION_STORY_LIBRARY: Dict[tuple[str, str], Dict[str, Any]] = {
    ("S1", "S2"): {
        "paragraphs": [
            "北平的枪声尚未停息，上海的战火已经压上案头。你收起初战时的慌乱，带着第一轮经验继续南下，报道开始进入更大范围的硬仗。",
            "你渐渐明白，战地记者不是跟在历史后面抄录的人，而是要在历史最混乱的时候，替人民把事实一层层捞出来。",
        ],
        "dialogues": [
            {
                "speaker": "陈编辑",
                "text": "{player_name}，别把上一稿当成结束。真正的考验，从来都是一稿接一稿、一仗接一仗。",
            }
        ],
    },
    ("S2", "S3"): {
        "paragraphs": [
            "前线消息一路南移，报道难题也从数字冲突，转向了对生命、隐私与线人安全的守护。",
            "你开始知道，有些最重要的真相，不是写得越满越好，而是要在保护人民的前提下，被稳稳地送出去。",
        ],
        "dialogues": [
            {
                "speaker": "林岚",
                "text": "会拍的人不一定懂得收，懂得收的人，才知道什么叫真正的分寸。写稿也是一样。",
            }
        ],
    },
    ("S3", "S4"): {
        "paragraphs": [
            "经历了生死线上的抉择后，你愈发明白：记者不仅记录苦难，也要帮助人民在苦难中找到行动方向。",
            "战时报道真正高明的地方，不是把恐惧渲染得多深，而是在最难的时候，仍能把组织、秩序与希望写出来。",
        ],
        "dialogues": [
            {
                "speaker": "陈编辑",
                "text": "你守住了一条底线，接下来要学会把底线变成力量，让群众知道下一步怎么走。",
            }
        ],
    },
    ("S4", "S5"): {
        "paragraphs": [
            "当战线拉长、捷报增多，考验不再只是敢不敢写，而是能不能把复杂信息分层，把胜利消息写得既振奋又扎实。",
            "你手里的笔，已经从记录现场，走向统筹判断；从单点核验，走向系统核验。",
        ],
        "dialogues": [
            {
                "speaker": "赵川",
                "text": "人容易在苦的时候慌，也容易在顺的时候松。能一直把笔握稳，才算真正长成了。",
            }
        ],
    },
    ("S5", "S6"): {
        "paragraphs": [
            "曙光已经在远处亮起。越接近历史转折，越需要一支沉稳的笔，把人民期待托住，把时代结论写准。",
            "最后一稿往往最难，因为所有人都急着欢呼，而你必须在欢呼声里继续守住确认边界。",
        ],
        "dialogues": [
            {
                "speaker": "陈编辑",
                "text": "真正成熟的记者，不是到了终局就放松，而是越到终局，越知道每个字都重。",
            }
        ],
    },
}


# 风险反馈按类型归类，避免所有负反馈都说成同一种口吻。
RISK_FEEDBACK_LIBRARY: Dict[str, Dict[str, Any]] = {
    "verification": {
        "paragraphs": [
            "《{scene_title}》这一轮结束后，编辑部的气氛一下子沉了下来。大家都清楚，战时报道最怕的不是慢半步，而是把未经证实的内容写成定论。",
            "你这一次碰到的提醒，本质上是在补一课：再急，也不能让失真的消息先于真实进入群众视野。",
            "如果一条稿件把“抢发”放在“求真”前面，损失的就不只是专业分数，更可能是人民对报馆的信任。",
        ],
        "dialogues": [
            {
                "speaker": "陈编辑",
                "text": "快，不该压倒准；响，不该压倒真。把这条记牢，你下一稿就能站得更稳。",
            }
        ],
    },
    "source_safety": {
        "paragraphs": [
            "《{scene_title}》这一轮结束后，几个人都沉默了片刻。大家心里都明白，战地报道一旦碰到来源暴露和隐私泄露，伤到的往往是最无力自保的人。",
            "这次提醒不是为了否定你继续前进的资格，而是在反复强调一条铁律：任何时候，都不能拿群众和线人的安全去换“更像真相”的表面效果。",
            "真正可靠的记者，不是把细节写得越满越好，而是知道哪些细节必须藏起来，才能让真相继续被送出来。",
        ],
        "dialogues": [
            {
                "speaker": "陈编辑",
                "text": "新闻人的勇敢，不是把别人推到危险里换稿件分量，而是在最难的时候，先把该保护的人保护住。",
            }
        ],
    },
    "public_panic": {
        "paragraphs": [
            "《{scene_title}》这一轮结束后，编辑部很快就抓住了问题症结：语言一旦越过边界，群众接收到的就不再是信息，而是恐慌。",
            "战时沟通不是把危险说得越吓人越好，而是要把真实风险和可执行行动一起交到人民手里。",
            "这一次的提醒，其实是在帮你学会更成熟的表达方式：既不掩盖困难，也不放大混乱。",
        ],
        "dialogues": [
            {
                "speaker": "基层干部",
                "text": "群众最怕的不是困难本身，而是不知道怎么办。写清楚方向，比一味渲染气氛更有力量。",
            }
        ],
    },
    "generic": {
        "paragraphs": [
            "《{scene_title}》这一轮结束后，编辑部很快进入复盘。大家都知道，训练的意义从来不是把人一棍子打下去，而是把问题尽早拎出来、尽早改明白。",
            "这次提醒说明你还有边界要继续磨，但方向并没有偏。只要肯复盘、肯修正，下一轮就能走得更稳。",
        ],
        "dialogues": [
            {
                "speaker": "陈编辑",
                "text": "问题发现得越早，成长就来得越快。别怕复盘，怕的是带着模糊继续往前冲。",
            }
        ],
    },
}


# 正向结局与历史化终章的映射同时兼容当前运行时名称和早期方案稿名称。
ENDING_STORY_LIBRARY: Dict[str, List[str]] = {
    "失真扩散": [
        "终章并不总是鲜花与掌声。有些结果之所以沉重，正因为它在提醒你：新闻的分寸一旦失守，代价往往会落在人民身上。",
        "但红色训练的意义，从来不是给人贴上失败标签，而是让人学会知责、改错、再出发。只要方向不偏，下一次落笔就会更稳、更亮。",
    ],
    "代价沉重": [
        "这一段路走得并不轻松。有些代价一旦发生，就会提醒你：真实、来源安全和群众利益，任何时候都不能被轻慢对待。",
        "可训练的价值，正在于把代价变成警醒，把警醒变成能力。只要肯复盘、肯修正，笔锋就还能重新站稳。",
    ],
    "艰难守真": [
        "你逐渐把“快”让位给“准”，把“刺激”让位给“可信”。这说明你已经开始理解，真正站得住的报道，根基永远在人民与事实之间。",
        "这样的成长不是终点，而是走向更高难度训练的起点。",
    ],
    "稳健求真": [
        "你逐渐把“快”让位给“准”，把“刺激”让位给“可信”。这说明你已经开始理解，真正站得住的报道，根基永远在人民与事实之间。",
        "这样的成长不是终点，而是走向更高难度训练的起点。",
    ],
    "逆风修正": [
        "你不是一路毫无偏差地走来，而是在压力与波动中学会了及时纠偏、及时修正。这样的成长，更能说明你已经具备真正走向成熟的底子。",
        "红色新闻训练看重的，从来不只是结果好不好看，更是能否在关键时刻把方向拉回来、把责任扛起来。",
    ],
    "人民信任": [
        "你把事实、分寸和人民立场一步步拧成了一股绳。稿子送出去的时候，传递的已不只是消息，还有可靠、冷静和希望。",
        "这正是红色新闻工作者最宝贵的气质：越在关键时刻，越能把笔锋落在人民需要的地方。",
    ],
    "史笔如铁": [
        "从战火初起到胜利到来，你已经不只是记录者，更是历史精神的传递者。你学会了在重大节点上稳住笔，也稳住人心。",
        "你的成长告诉人们，真实、责任与信念，永远是穿透风云的力量。",
    ],
    "胜利见证": [
        "从战火初起到胜利到来，你已经不只是记录者，更是历史精神的传递者。你学会了在重大节点上稳住笔，也稳住人心。",
        "你的成长告诉人们，真实、责任与信念，永远是穿透风云的力量。",
    ],
}


class _SafeFormatDict(dict):
    """为剧本模板提供安全格式化，缺字段时回退为空字符串。"""

    def __missing__(self, key: str) -> str:
        return ""


def _resolve_player_name(player_profile: Dict[str, Any] | None) -> str:
    """解析玩家姓名，缺失时给出稳妥称呼。"""
    if not isinstance(player_profile, dict):
        return "你"
    player_name = str(player_profile.get("name") or "").strip()
    return player_name or "你"


def _resolve_player_identity(player_profile: Dict[str, Any] | None) -> str:
    """解析玩家身份，缺失时回退到通用称呼。"""
    if not isinstance(player_profile, dict):
        return "战地记者"
    identity = str(player_profile.get("identity") or "").strip()
    return identity or "战地记者"


def _build_dialogue_block(dialogues: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """统一过滤对白结构，避免脚本层把空对白带给 CLI。"""
    normalized_dialogues: List[Dict[str, str]] = []
    for item in dialogues:
        speaker = str(item.get("speaker") or "").strip()
        text = str(item.get("text") or "").strip()
        if not speaker or not text:
            continue
        normalized_dialogues.append({"speaker": speaker, "text": text})
    return normalized_dialogues


def _strip_terminal_punctuation(text: str) -> str:
    """去掉句末重复标点，避免模板再次补句号时出现双标点。"""
    return str(text or "").strip().rstrip("。！!？?,，；;：:")


def _build_format_context(
    scenario: Dict[str, Any] | None = None,
    player_profile: Dict[str, Any] | None = None,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, str]:
    """统一构建剧本模板渲染上下文。"""
    payload = dict(scenario or {})
    context = {
        "player_name": _resolve_player_name(player_profile),
        "player_identity": _resolve_player_identity(player_profile),
        "scene_id": str(payload.get("id") or "").strip(),
        "scene_title": str(payload.get("title") or "").strip(),
        "era_date": str(payload.get("era_date") or "").strip(),
        "location": str(payload.get("location") or "").strip(),
        "brief": str(payload.get("brief") or "").strip(),
        "mission": _strip_terminal_punctuation(str(payload.get("mission") or "").strip()),
        "decision_focus": str(payload.get("decision_focus") or "").strip(),
        "completion_hint": str(payload.get("completion_hint") or "").strip(),
    }
    for key, value in dict(extra or {}).items():
        context[str(key)] = str(value or "").strip()
    return context


def _render_templates(templates: List[str], context: Dict[str, str]) -> List[str]:
    """按统一上下文渲染段落模板。"""
    safe_context = _SafeFormatDict(context)
    rendered: List[str] = []
    for template in templates:
        text = str(template or "").strip().format_map(safe_context)
        if text:
            rendered.append(text)
    return rendered


def _render_dialogue_templates(dialogues: List[Dict[str, str]], context: Dict[str, str]) -> List[Dict[str, str]]:
    """按统一上下文渲染对白模板。"""
    safe_context = _SafeFormatDict(context)
    rendered: List[Dict[str, str]] = []
    for item in dialogues:
        speaker = str(item.get("speaker") or "").strip().format_map(safe_context)
        text = str(item.get("text") or "").strip().format_map(safe_context)
        if speaker and text:
            rendered.append({"speaker": speaker, "text": text})
    return _build_dialogue_block(rendered)


def _resolve_option_label(scenario: Dict[str, Any], selected_option: str | None) -> str:
    """把选项 ID 解析成人能读懂的标签。"""
    option_id = str(selected_option or "").strip()
    if not option_id:
        return ""
    for option in list(scenario.get("options") or []):
        current_id = str(option.get("id") or "").strip()
        if current_id == option_id:
            return str(option.get("label") or option_id).strip()
    return option_id


def _resolve_primary_risk_type(risk_flags: List[str]) -> str:
    """根据风险标签归类编辑部反馈类型。"""
    normalized_flags = [str(item or "").strip().lower() for item in risk_flags if str(item or "").strip()]
    if any(flag in {"source_exposure_risk", "privacy_leak_risk"} for flag in normalized_flags):
        return "source_safety"
    if any(flag in {"high_risk_unverified_publish", "rumor_spread_risk"} for flag in normalized_flags):
        return "verification"
    if any("panic" in flag for flag in normalized_flags):
        return "public_panic"
    return "generic"


def build_story_prologue_block(
    player_profile: Dict[str, Any] | None,
    training_mode: str,
) -> Dict[str, Any]:
    """构建训练开场的总序章。"""
    player_name = _resolve_player_name(player_profile)
    player_identity = _resolve_player_identity(player_profile)
    return {
        "title": "序章：烽火笔锋",
        "paragraphs": [
            "以下剧本以抗战时期重大历史节点为背景，人物与对白为基于史实精神的艺术化再创作。",
            "1937 年夏，山河破碎、烽火骤起，无数军民在民族危亡之际挺身而出。报馆里的一篇篇稿件，也成了战时精神动员与事实传播的重要一环。",
            f"{player_name}，你将以{player_identity}的身份进入一条跨越 1937 至 1945 年的战地报道成长线。从这一刻起，你面对的不只是题目，而是一次次关于人民立场、事实核验、线人保护和公共引导的实战演练。",
            f"当前训练模式为 {training_mode}。这条路不会只奖励会写的人，更会考验谁能在最复杂的局势中，把真实、责任和希望一起写出来。",
        ],
        "dialogues": _build_dialogue_block(
            [
                {
                    "speaker": "陈编辑",
                    "text": f"{player_name}，从今天起，你写下的每一行字，都要对得起山河、对得起同胞、也对得起新闻人的良知。",
                },
                {
                    "speaker": "老通讯员赵川",
                    "text": "战火越急，越要稳住笔。我们要把真实告诉人民，也要把信心送到人民中间。",
                },
                {
                    "speaker": "印刷工老何",
                    "text": "纸张会旧，铅字会凉，但真正站得住的报道，能陪很多人熬过最难的夜。",
                },
            ]
        ),
    }


def build_scene_story_block(
    scenario: Dict[str, Any],
    player_profile: Dict[str, Any] | None,
    round_no: int,
) -> Dict[str, Any]:
    """根据当前场景生成开场叙事与对白。"""
    scene_id = str(scenario.get("id") or "").strip()
    scene_title = str(scenario.get("title") or scene_id)
    context = _build_format_context(scenario=scenario, player_profile=player_profile)

    scene_script = SCENE_STORY_LIBRARY.get(scene_id)
    if not scene_script:
        return {
            "title": f"第 {round_no} 回：{scene_title}",
            "paragraphs": [
                f"历史背景：{context['era_date']}，地点为{context['location']}。",
                f"{context['player_name']}走进{scene_title}，准备在复杂局势中完成这一次训练任务。",
                f"本回任务是：{context['mission']}。你要继续围绕“{context['decision_focus']}”稳住判断与表达。",
            ],
            "dialogues": [],
        }

    return {
        "title": f"第 {round_no} 回：{scene_title}",
        "paragraphs": _render_templates(list(scene_script.get("paragraphs") or []), context),
        "dialogues": _render_dialogue_templates(list(scene_script.get("dialogues") or []), context),
    }


def build_round_feedback_story_block(
    scenario: Dict[str, Any],
    submit_result: Dict[str, Any],
    selected_option: str | None = None,
    user_input: str | None = None,
) -> Dict[str, Any]:
    """根据回合提交结果生成人物反馈。"""
    scene_title = str(scenario.get("title") or scenario.get("id") or "当前场景")
    evaluation = dict(submit_result.get("evaluation") or {})
    risk_flags = [str(item) for item in evaluation.get("risk_flags") or [] if str(item).strip()]
    evidence = [str(item) for item in evaluation.get("evidence") or [] if str(item).strip()]
    option_label = _resolve_option_label(scenario, selected_option)
    user_input_preview = str(user_input or "").strip()
    if len(user_input_preview) > 28:
        user_input_preview = f"{user_input_preview[:28]}..."

    context = _build_format_context(
        scenario=scenario,
        extra={
            "scene_title": scene_title,
            "option_label": option_label,
            "user_input_preview": user_input_preview,
        },
    )

    if risk_flags:
        feedback_template = RISK_FEEDBACK_LIBRARY[_resolve_primary_risk_type(risk_flags)]
        paragraphs = _render_templates(list(feedback_template.get("paragraphs") or []), context)
        if option_label:
            paragraphs.insert(1, f"你本轮采取的是“{option_label}”这一处理思路，编辑部因此进一步追问其中的边界与后果。")
        if evidence:
            paragraphs.append(f"编辑部复盘要点：{evidence[0]}")
        dialogues = _render_dialogue_templates(list(feedback_template.get("dialogues") or []), context)
    else:
        paragraphs = [
            f"《{scene_title}》这一轮结束后，报馆里没有喧闹，只有一种沉稳的踏实感。你在压力中把分寸守住了。",
            "这样的进步未必轰轰烈烈，却正是红色新闻训练最看重的力量：越紧要，越守原则；越复杂，越见担当。",
        ]
        if option_label:
            paragraphs.append(f"你这一次选择了“{option_label}”，这说明你已经开始把“{context['decision_focus']}”真正落实到处理策略上。")
        if evidence:
            paragraphs.append(f"本轮关键收获：{evidence[0]}")
        dialogues = _render_dialogue_templates(
            [
                {
                    "speaker": "陈编辑",
                    "text": "这回你写得稳。新闻人的骨气，不在声高，而在关键时刻把真相、人民和责任放在一条线上。",
                },
                {
                    "speaker": "赵川",
                    "text": "稿子稳一分，人心就稳一分。你这一路，确实在长本事。",
                },
            ],
            context,
        )

    return {
        "title": "过场：编辑部回响",
        "paragraphs": paragraphs,
        "dialogues": dialogues,
    }


def build_transition_story_block(
    current_scenario: Dict[str, Any],
    next_scenario: Dict[str, Any] | None,
    player_profile: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """为相邻场景补一段历史过场，把六个节点串成完整成长线。"""
    if not isinstance(next_scenario, dict) or not next_scenario:
        return None

    current_id = str(current_scenario.get("id") or "").strip()
    next_id = str(next_scenario.get("id") or "").strip()
    transition_script = TRANSITION_STORY_LIBRARY.get((current_id, next_id))
    if not transition_script:
        return None

    context = _build_format_context(scenario=next_scenario, player_profile=player_profile)
    return {
        "title": "转场",
        "paragraphs": _render_templates(list(transition_script.get("paragraphs") or []), context),
        "dialogues": _render_dialogue_templates(list(transition_script.get("dialogues") or []), context),
    }


def build_story_epilogue_block(
    player_profile: Dict[str, Any] | None,
    report_result: Dict[str, Any],
) -> Dict[str, Any]:
    """根据训练报告输出终章叙事。"""
    player_name = _resolve_player_name(player_profile)
    player_identity = _resolve_player_identity(player_profile)
    ending_payload = dict(report_result.get("ending") or {})
    ending_type = str(ending_payload.get("ending_type") or ending_payload.get("type") or "").strip()
    summary = dict(report_result.get("summary") or {})
    weakest_skill_code = str(summary.get("weakest_skill_code") or "").strip()
    strongest_skill_code = str(summary.get("strongest_improved_skill_code") or "").strip()
    completed_scenario_ids = [str(item) for item in summary.get("completed_scenario_ids") or [] if str(item).strip()]

    paragraphs = list(
        ENDING_STORY_LIBRARY.get(
            ending_type,
            [
                "训练暂时告一段落，但新闻人的路从不会在一次结局里停止。每一次复盘，都是为了下一次更稳、更准、更有力量地出发。",
                "只要始终把人民立场、事实边界和历史责任放在心里，这支笔就会越来越有方向。",
            ],
        )
    )
    if completed_scenario_ids:
        paragraphs.append(
            f"从卢沟桥到终战节点，你已经走过 {len(completed_scenario_ids)} 个历史训练关口。对于{player_identity}而言，这不只是流程走完，更是一条把笔锋磨进时代风云中的成长线。"
        )
    if strongest_skill_code:
        paragraphs.append(f"这一程里，你最明显的成长点落在 {strongest_skill_code}。这意味着你已经开始把一些正确做法，从“知道”走向“做稳”。")
    if weakest_skill_code:
        paragraphs.append(f"下一阶段，你仍可以继续围绕 {weakest_skill_code} 进行补练，把短板补齐，把长处打磨得更锋利。")

    return {
        "title": "终章：把笔锋写进时代",
        "paragraphs": paragraphs,
        "dialogues": _build_dialogue_block(
            [
                {
                    "speaker": "陈编辑",
                    "text": f"{player_name}，真正的好记者，不是永远不犯错，而是每一次都能向着人民、向着真相、向着胜利再走近一步。",
                },
                {
                    "speaker": "老何",
                    "text": "稿子写完了，路却还长。只要心里装着人民，这支笔就会越写越有光。",
                },
            ]
        ),
    }
