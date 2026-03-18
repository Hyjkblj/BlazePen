"""AI文本生成模块 - 使用通用LLM框架"""
import json
import re
from typing import Optional, List, Dict

from llm import LLMService, LLMException


class AIGenerator:
    """AI文本生成器（业务层，使用通用LLM框架）"""
    
    def __init__(self, provider: Optional[str] = None):
        """初始化AI生成器
        
        Args:
            provider: 提供商名称（'openai', 'volcengine', 'dashscope', 'auto'），如果为None则自动检测
        """
        try:
            self.llm_service = LLMService(provider=provider or 'auto')
            self.enabled = True
            print(f"[AI生成器] 已启用 - 提供商: {self.llm_service.get_provider()}, 模型: {self.llm_service.get_model()}")
        except LLMException as e:
            self.llm_service = None
            self.enabled = False
            print(f"[警告] AI生成器初始化失败: {e}")
            print("[警告] 将使用规则生成")
    
    def _call_text_generation(self, prompt: str, max_tokens: int = 200, temperature: float = 0.7) -> Optional[str]:
        """统一的文本生成调用接口（兼容旧代码）
        
        Args:
            prompt: 提示词
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            生成的文本，如果失败返回None
        """
        if not self.enabled or not self.llm_service:
            return None
        
        try:
            return self.llm_service.chat_completion(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                use_retry=True
            )
        except LLMException as e:
            print(f"[警告] 文本生成失败: {e}")
            return None
    
    def generate_story_background(self, character_id: int, previous_events: List[str], 
                                  current_context: str, character_name: str = None) -> str:
        """生成故事背景文本（必须基于向量数据库检索的历史事件）
        
        Args:
            character_id: 角色ID
            previous_events: 历史事件列表（从向量数据库检索，必须提供）
            current_context: 当前事件上下文
            character_name: 角色名称（用于在文本中标识）
            
        Returns:
            生成的故事背景文本（包含player和角色名）
        """
        # 如果没有历史事件，从向量数据库检索
        if not previous_events or len(previous_events) == 0:
            print("[警告] generate_story_background未提供历史事件，应该从向量数据库检索")
        
        if not self.enabled:
            # 回退到规则生成
            if previous_events:
                return f"基于过往的经历，player和{character_name or '角色'}继续他们的故事。{previous_events[0][:200]}..."
            return f"这是一个新的开始。player和{character_name or '角色'}开始了新的相遇。{current_context}"
        
        # 构建提示词（强调必须基于历史事件）
        previous_context = "\n".join([f"- {event}" for event in previous_events[:5]]) if previous_events else "这是第一次相遇，没有历史事件。"
        
        # 如果没有提供角色名，尝试从数据库获取
        if not character_name:
            try:
                from database.db_manager import DatabaseManager
                db_manager = DatabaseManager()
                character = db_manager.get_character(character_id)
                if character:
                    character_name = character.name
            except:
                character_name = "角色"
        
        prompt = f"""你是一个剧情游戏的故事背景生成器。请根据以下信息生成一段故事背景描述（100-150字）：

【重要】必须基于历史事件生成，不能脱离历史事件凭空创造！
【时间设定】故事发生在当下（现代），禁止出现"20世纪初/古代/民国/未来"等年代背景。

【历史事件】（必须参考，确保连续性）：
{previous_context}

【当前情境】：
{current_context}

【角色信息】：
- 玩家：player
- 角色：{character_name}

要求：
1. 【必须基于历史】必须基于历史事件合理推演新的事件发展，不能脱离历史事件
2. 【连续性】新事件必须与历史事件有明确的因果关系或时间顺序
3. 【明确标识】在描述中明确使用"player"和"{character_name}"来标识玩家和角色，不要混淆
4. 【不重复】不要重复之前已经发生过的场景和事件，要推进剧情发展
5. 【场景切换】可以自然地切换场景，但要符合逻辑，有合理的过渡
6. 【剧情推进】描述场景和发生了什么，让剧情有新的进展
7. 【场景描述】明确描述当前场景，让玩家知道在哪里
8. 【第三人称】使用第三人称描述，例如："player和{character_name}在图书馆相遇..."
9. 语言自然流畅，符合剧情发展
10. 不要包含角色对话，只描述背景和事件
11. 如果历史事件中有约定或承诺，可以在新事件中体现
12. 【当下语境】用当代校园/日常生活语境与细节，不要出现年代错位的道具与社会背景。

故事背景（必须包含player和{character_name}的名字）："""
        
        try:
            result = self._call_text_generation(prompt, max_tokens=300, temperature=0.8)
            if result:
                return result
            else:
                return self._fallback_story(previous_events, current_context)
        except Exception as e:
            print(f"[错误] AI生成异常: {e}")
            return self._fallback_story(previous_events, current_context)
    
    def generate_character_dialogue(self, story_background: str, character_info: Dict, 
                                    state_values: Dict, dialogue_round: int = 1, 
                                    previous_dialogues: List[str] = None, 
                                    character_name: str = None,
                                    historical_impacts: List[str] = None) -> str:
        """生成角色对话文本
        
        Args:
            story_background: 故事背景文本
            character_info: 角色信息（包含决定因素）
            state_values: 状态值
            dialogue_round: 对话轮次（1-4+）
            previous_dialogues: 之前的完整对话历史
            character_name: 角色名称
            historical_impacts: 玩家历史选项的影响
            
        Returns:
            生成的角色对话文本
        """
        if not self.enabled:
            return self._fallback_dialogue(character_info, state_values)
        
        # 构建完整的角色属性描述（提高权重）
        # 优先使用字典格式的性格（新系统）
        personality_dict = character_info.get('personality', {})
        if isinstance(personality_dict, dict):
            # 从字典中提取性格关键词
            personality_keywords = personality_dict.get('keywords', [])
            personality_text = '，'.join(personality_keywords) if personality_keywords else character_info.get('personality_text', '')
        else:
            personality_text = personality_dict if personality_dict else character_info.get('personality_text', '')
        
        gender = character_info.get('gender', '')
        appearance = character_info.get('appearance', '')
        attributes = character_info.get('attributes', {})
        
        # 提取所有角色属性（用于更详细的角色描述）
        background = attributes.get('出身背景', '')
        family_background = attributes.get('家庭背景', '')
        social_identity = attributes.get('社会身份', '')
        education = attributes.get('教育经历', '')
        interests = attributes.get('兴趣偏好', '')
        values = attributes.get('价值观体系', '')
        flaws = attributes.get('角色缺陷', '')
        fears = attributes.get('害怕与禁忌', '')
        relationship_style = attributes.get('人际关系风格', '')
        love_style = attributes.get('爱情风格', '')
        trust_model = attributes.get('信任模型', '')
        development_curve = attributes.get('发展曲线', '')
        
        # 构建详细的状态值描述（提高权重）
        favorability = state_values.get('favorability', 0)
        trust = state_values.get('trust', 0)
        hostility = state_values.get('hostility', 0)
        dependence = state_values.get('dependence', 0)
        emotion = state_values.get('emotion', 50)
        stress = state_values.get('stress', 0)
        anxiety = state_values.get('anxiety', 0)
        happiness = state_values.get('happiness', 50)
        sadness = state_values.get('sadness', 0)
        confidence = state_values.get('confidence', 50)
        initiative = state_values.get('initiative', 50)
        caution = state_values.get('caution', 50)
        
        # 构建状态值影响描述（更详细，权重更高）
        state_impact = []
        if favorability > 60:
            state_impact.append("对玩家非常有好感，态度友好热情")
        elif favorability > 30:
            state_impact.append("对玩家有好感，态度友善")
        elif favorability < -30:
            state_impact.append("对玩家有敌意，态度冷淡")
        elif favorability < 0:
            state_impact.append("对玩家印象不佳，态度疏远")
        else:
            state_impact.append("对玩家印象中性，态度平常")
        
        if trust > 60:
            state_impact.append("非常信任玩家，愿意分享内心想法")
        elif trust > 30:
            state_impact.append("信任玩家，愿意交流")
        elif trust < -30:
            state_impact.append("不信任玩家，保持警惕")
        elif trust < 0:
            state_impact.append("对玩家有疑虑，保持距离")
        
        if confidence > 70:
            state_impact.append("非常自信，说话果断")
        elif confidence < 30:
            state_impact.append("缺乏自信，说话犹豫")
        
        if happiness > 70:
            state_impact.append("心情很好，语气轻松愉快")
        elif happiness < 30:
            state_impact.append("心情低落，语气沉重")
        
        if stress > 70:
            state_impact.append("压力很大，显得焦虑紧张")
        elif stress > 40:
            state_impact.append("有一定压力，略显疲惫")
        
        state_desc = "；".join(state_impact) if state_impact else "状态正常"
        
        # 构建完整的角色属性描述（强调这些对对话的影响）
        character_attributes_desc = f"""
【核心性格】{personality_text}
【性别】{gender}
【外观】{appearance}
【出身背景】{background}
【家庭背景】{family_background}
【社会身份】{social_identity}
【教育经历】{education}
【兴趣偏好】{interests}
【价值观】{values}
【性格缺陷】{flaws}
【害怕与禁忌】{fears}
【人际关系风格】{relationship_style}
【爱情风格】{love_style}
【信任模型】{trust_model}
【发展曲线】{development_curve}"""
        
        # 构建之前的对话上下文（区分当前事件对话和向量数据库历史对话）
        previous_context = ""
        if previous_dialogues and len(previous_dialogues) > 0:
            # 区分当前事件的对话和向量数据库中的历史对话
            current_event_dialogues = []
            vector_db_dialogues = []
            
            for item in previous_dialogues:
                if isinstance(item, str):
                    if item.startswith("[历史"):
                        # 兼容 [历史] / [历史对话] / [历史事件] 等标签
                        vector_db_dialogues.append(re.sub(r'^\[历史[^\]]*\]\s*', '', item).strip())
                    else:
                        current_event_dialogues.append(item)
                else:
                    current_event_dialogues.append(str(item))
            
            # 构建上下文
            context_parts = []
            if current_event_dialogues:
                context_parts.append("当前事件的对话：\n" + "\n".join(current_event_dialogues[-4:]))
            if vector_db_dialogues:
                context_parts.append("历史对话（从向量数据库检索，用于推演）：\n" + "\n".join(vector_db_dialogues[-3:]))
            
            previous_context = "\n之前的对话：\n" + "\n".join(context_parts) if context_parts else "\n这是第一轮对话。"
        else:
            previous_context = "\n这是第一轮对话。"
        
        # 根据对话轮次确定对话的作用
        dialogue_role = ""
        if dialogue_round == 1:
            dialogue_role = "开场/引入话题，开启对话"
        elif dialogue_round == 2:
            dialogue_role = "发展/深入讨论，推进话题"
        elif dialogue_round == 3:
            dialogue_role = "继续发展/深入交流，深化关系"
        else:
            dialogue_role = "结尾/总结/推进剧情，为事件收尾"
        
        # 如果没有提供角色名，尝试从character_info获取
        if not character_name:
            # character_info可能包含name字段，或者需要从数据库获取
            character_name = character_info.get('name', '角色')
        
        # 提取之前所有角色对话，用于避免重复
        previous_character_dialogues = []
        if previous_dialogues:
            for item in previous_dialogues:
                if isinstance(item, str):
                    # 检查格式："{角色名}: ..." 或 "角色: ..."
                    if f"{character_name}:" in item:
                        previous_character_dialogues.append(item.split(f"{character_name}:")[-1].strip())
                    elif item.startswith("角色:"):
                        previous_character_dialogues.append(item.replace("角色:", "").strip())
                elif isinstance(item, dict) and item.get('type') == 'character':
                    previous_character_dialogues.append(item.get('content', ''))
        
        previous_char_dialogues_text = ""
        if previous_character_dialogues:
            previous_char_dialogues_text = "\n之前角色说过的话（不要重复相似内容）：\n" + "\n".join([f"- {d}" for d in previous_character_dialogues])
        
        # 构建玩家历史选项的影响描述
        historical_impacts_text = ""
        if historical_impacts:
            historical_impacts_text = "\n【玩家历史选项的影响】（参考，影响角色当前态度）：\n" + "\n".join([f"- {impact}" for impact in historical_impacts[-3:]])
        
        prompt = f"""你是一个剧情游戏的角色对话生成器。请根据以下信息生成角色的对话（20-40字）：

【故事背景】（参考）：
{story_background}

【时间设定】故事发生在当下（现代），不要出现年代错位背景。

【历史对话】（参考，保持连贯，必须基于这些对话生成）：
{previous_context}
{previous_char_dialogues_text}

【角色完整属性】（【最高优先级】必须严格遵循，这些属性决定角色的说话方式、用词、语气）：
{character_attributes_desc}

【角色性格】（【最高优先级】必须严格遵循，不同性格在同一情绪状态下说话方式完全不同）：
性格关键词：{personality_text}
- 性格直接影响对话风格：高冷性格说话简洁冷淡，热情性格说话热情主动，内向性格说话含蓄谨慎
- 必须严格符合角色性格，不能脱离性格特征
{historical_impacts_text}

【当前状态值】（【最高优先级】必须严格遵循，这些状态值直接影响角色的语气、态度、情绪）：
{state_desc}
详细数值：好感度{favorability:.0f}，信任度{trust:.0f}，敌意{hostility:.0f}，依赖度{dependence:.0f}，情绪{emotion:.0f}，压力{stress:.0f}，焦虑{anxiety:.0f}，快乐{happiness:.0f}，悲伤{sadness:.0f}，自信度{confidence:.0f}，主动度{initiative:.0f}，谨慎度{caution:.0f}

【角色名称】：{character_name}
【玩家名称】：player

对话轮次：第{dialogue_round}轮对话（最多5轮）
本轮对话作用：{dialogue_role}

【核心要求】（按优先级排序）：
1. 【必须基于历史】必须基于历史对话内容生成，不能脱离历史对话
2. 【最高优先级】对话必须严格符合角色性格（{personality_text}），不同性格在同一情绪状态下说话方式完全不同
3. 【最高优先级】对话必须严格反映当前状态值（好感度、信任度、情绪等），状态值直接影响语气和态度
4. 【最高优先级】对话必须考虑玩家历史选项的影响，这些影响会影响角色对玩家的态度
4. 【格式要求】对话必须以"{character_name}:"开头，例如："{character_name}: 你好，很高兴认识你"
5. 【重要】对话要回应故事背景中的事件，但不能脱离角色属性
6. 【重要】必须基于之前的对话内容，承上启下，保持连贯性
7. 【禁止】绝对不要重复之前角色说过的话，内容、意思、表达方式都要完全不同
8. 【禁止】绝对不要使用玩家可能说的话，角色对话和玩家选项必须完全隔离
9. 【禁止】不要混淆player和{character_name}，角色对话必须是{character_name}说的话
10. 如果之前有对话，要回应player的话或继续之前的话题，但要推进剧情
11. 语言自然，像真实对话，但要符合角色属性
12. 对话要有头有尾，能够完整概述事件或承上启下

角色对话（必须以"{character_name}:"开头）："""
        
        try:
            result = self._call_text_generation(prompt, max_tokens=100, temperature=0.9)
            if result:
                dialogue = result.strip()
                # 清理可能的引号和其他标记
                dialogue = dialogue.strip('"').strip("'").strip()
                
                # 确保对话包含角色名
                if not dialogue.startswith(f"{character_name}:") and not dialogue.startswith(f"{character_name}："):
                    # 如果AI没有加上名字，我们加上
                    dialogue = f"{character_name}: {dialogue}"
                else:
                    # 清理可能的重复前缀
                    if dialogue.startswith(f"{character_name}："):
                        dialogue = dialogue.replace(f"{character_name}：", f"{character_name}:", 1)
                
                # 检查是否与之前的角色对话重复
                if previous_character_dialogues:
                    dialogue = self._ensure_dialogue_unique(dialogue, previous_character_dialogues, dialogue_round)
                
                return dialogue
            else:
                return self._fallback_dialogue(character_info, state_values)
        except Exception as e:
            print(f"[错误] AI生成异常: {e}")
            return self._fallback_dialogue(character_info, state_values)
    
    def generate_player_options(self, story_background: str, character_dialogue: str, 
                                dialogue_round: int, previous_dialogues: List[str] = None,
                                personality_dict: dict = None, current_states: object = None) -> List[Dict]:
        """生成玩家选项（对话内容）
        
        Args:
            story_background: 故事背景
            character_dialogue: 角色刚才说的话
            dialogue_round: 对话轮次
            previous_dialogues: 之前的完整对话历史（用于保持对话连贯）
            personality_dict: 角色性格字典
            current_states: 当前状态对象
            
        Returns:
            3个选项，每个选项包含对话文本和状态值变化
        """
        if not self.enabled:
            return self._fallback_options()
        
        # 构建之前的对话上下文（区分当前事件对话和向量数据库历史对话）
        previous_context = ""
        if previous_dialogues and len(previous_dialogues) > 0:
            # 区分当前事件的对话和向量数据库中的历史对话
            current_event_dialogues = []
            vector_db_dialogues = []
            
            for item in previous_dialogues:
                if isinstance(item, str):
                    if item.startswith("[历史"):
                        # 兼容 [历史] / [历史对话] / [历史事件] 等标签
                        vector_db_dialogues.append(re.sub(r'^\[历史[^\]]*\]\s*', '', item).strip())
                    else:
                        current_event_dialogues.append(item)
                else:
                    current_event_dialogues.append(str(item))
            
            # 构建上下文
            context_parts = []
            if current_event_dialogues:
                context_parts.append("当前事件的对话：\n" + "\n".join(current_event_dialogues[-4:]))
            if vector_db_dialogues:
                context_parts.append("历史对话（从向量数据库检索，用于推演）：\n" + "\n".join(vector_db_dialogues[-3:]))
            
            previous_context = "\n之前的对话：\n" + "\n".join(context_parts) if context_parts else "\n这是第一轮对话。"
        else:
            previous_context = "\n这是第一轮对话。"
        
        # 提取之前所有玩家选项，避免重复
        previous_player_options = []
        if previous_dialogues:
            for item in previous_dialogues:
                if isinstance(item, str):
                    if item.startswith("玩家:"):
                        previous_player_options.append(item.replace("玩家:", "").strip())
                    # 也检查向量数据库中的历史对话
                    elif "玩家:" in item:
                        previous_player_options.append(item.split("玩家:")[-1].strip())
                elif isinstance(item, dict) and item.get('type') == 'player':
                    previous_player_options.append(item.get('content', ''))
        
        previous_options_text = ""
        if previous_player_options:
            previous_options_text = "\n之前玩家说过的话（不要重复相似内容）：\n" + "\n".join([f"- {d}" for d in previous_player_options[-3:]])
        
        # 根据对话轮次确定对话的作用
        dialogue_role = ""
        if dialogue_round == 1:
            dialogue_role = "开场/回应开场，开启对话"
        elif dialogue_round == 2:
            dialogue_role = "发展/深入讨论，推进话题"
        elif dialogue_round == 3:
            dialogue_role = "继续发展/深化关系，深入交流"
        else:
            dialogue_role = "结尾/总结/推进剧情，为事件收尾"
        
        prompt = f"""你是一个剧情游戏的玩家选项生成器。请根据以下信息生成3个玩家回复选项：

【故事背景】（参考）：
{story_background}

【时间设定】故事发生在当下（现代），不要出现年代错位背景。

【历史对话】（参考，保持连贯，必须基于这些对话生成）：
{previous_context}
{previous_options_text}

【角色刚才说的话】（必须回应）：
"{character_dialogue}"

【玩家名称】：player

对话轮次：第{dialogue_round}轮（最多5轮）
本轮对话作用：{dialogue_role}

【核心要求】（按优先级排序）：
1. 【必须基于历史】必须基于历史对话内容生成，不能脱离历史对话
2. 【最高优先级】生成3个不同的玩家回复选项，每个10-25字
3. 【格式要求】每个选项直接输出文本，不要添加"player:"前缀
4. 【最高优先级】选项1：积极回应（会提升好感度和信任度）- 友好、支持、鼓励
5. 【最高优先级】选项2：中性回应（保持现状）- 中立、观察、不表态
6. 【最高优先级】选项3：消极回应（会降低好感度和信任度）- 冷淡、拒绝、质疑
7. 【重要】必须直接回应角色刚才说的话，不能脱离角色对话
8. 【重要】必须考虑之前的对话内容，保持连贯性
9. 【重要】回复要符合当前场景和事件背景
10. 【禁止】绝对不要重复角色刚才说的话，玩家选项和角色对话必须完全隔离
11. 【禁止】绝对不要使用角色可能说的话，玩家选项必须是玩家说的话
12. 【禁止】不要重复之前玩家说过的话，内容、意思、表达方式都要完全不同
13. 【禁止】不要模仿角色的说话风格，玩家选项应该有自己的表达方式
14. 【禁止】不要混淆player和角色，玩家选项必须是player说的话
15. 回复要像真实对话，自然流畅，但必须是玩家的表达方式
16. 对话要有头有尾，能够完整概述事件或承上启下
17. 格式：每行一个选项，直接输出文本内容，不要添加任何前缀

【隔离要求】（非常重要）：
- 玩家选项必须与角色对话完全隔离
- 不能使用角色说过的话
- 不能使用角色的表达方式
- 必须是玩家自己的说话风格

玩家选项（直接输出文本，每行一个选项）："""
        
        try:
            result = self._call_text_generation(prompt, max_tokens=150, temperature=0.9)
            if result:
                options_text = result.strip()
                # 解析选项
                options = self._parse_options(options_text)
                
                # 过滤掉与角色对话重复的选项
                options = self._filter_duplicate_options(options, character_dialogue)
                
                # 如果过滤后选项不足3个，尝试重新生成或补充
                if len(options) < 3:
                    # 尝试补充选项
                    options = self._supplement_options(options, character_dialogue, story_background, previous_dialogues)
                
                # 为每个选项动态计算状态值变化（根据角色性格和当前情绪状态）
                if len(options) >= 3:
                    return [
                        {
                            'id': 1,
                            'text': options[0],
                            'type': 'increase',
                            'state_changes': self._calculate_dynamic_state_changes(
                                personality_dict=personality_dict,
                                current_states=current_states,
                                option_type='increase'
                            )
                        },
                        {
                            'id': 2,
                            'text': options[1],
                            'type': 'neutral',
                            'state_changes': {}
                        },
                        {
                            'id': 3,
                            'text': options[2],
                            'type': 'decrease',
                            'state_changes': self._calculate_dynamic_state_changes(
                                personality_dict=personality_dict,
                                current_states=current_states,
                                option_type='decrease'
                            )
                        }
                    ]
                else:
                    return self._fallback_options()
            else:
                return self._fallback_options()
        except Exception as e:
            print(f"[错误] AI生成异常: {e}")
            return self._fallback_options()
    
    def _parse_options(self, text: str) -> List[str]:
        """解析AI生成的选项文本，去除player:前缀"""
        if not text:
            return ["我明白了", "继续", "好的"]

        def _clean_option(raw: object) -> Optional[str]:
            if raw is None:
                return None

            line = str(raw).strip()
            if not line:
                return None

            # 移除列表序号/项目符号前缀
            line = re.sub(r'^\s*(?:[-*•]+|\d+\s*[\.、:：)\-]|[A-Za-z]\s*[\.、:：)\-])\s*', '', line)
            # 去除可能的引号
            line = line.strip().strip('"').strip("'").strip('“”')

            # 去除玩家前缀
            line = re.sub(r'^(?:player|玩家)[：:]\s*', '', line, flags=re.IGNORECASE)
            if not line:
                return None

            lower = line.lower()
            # 过滤常见说明性前言，避免被当成选项
            if lower.startswith(("here are", "options", "choices", "player options")):
                return None
            if line.startswith(("以下是", "下面是", "当然", "玩家选项", "可选项", "选项如下")):
                return None
            if re.search(r'\b(here are|options?|choices?)\b', lower) and (':' in line or '：' in line):
                return None
            if re.match(r'^(?:options?|choices?|player_options?)\s*[：:]\s*$', lower):
                return None
            if re.match(r'^(?:option|选项)\s*\d+\s*$', lower):
                return None

            return line if len(line) >= 2 else None

        options: List[str] = []

        def _append_options(raw_items: List[object]) -> None:
            for item in raw_items:
                if isinstance(item, dict):
                    item = item.get('text') or item.get('content') or item.get('option')
                cleaned = _clean_option(item)
                if cleaned and cleaned not in options:
                    options.append(cleaned)
                if len(options) >= 3:
                    return

        # 优先尝试按 JSON 解析，兼容数组/对象与 markdown 代码块
        json_candidates = [text.strip()]
        fence_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, flags=re.IGNORECASE | re.DOTALL)
        if fence_match:
            json_candidates.insert(0, fence_match.group(1).strip())
        array_match = re.search(r'\[[\s\S]*\]', text)
        if array_match:
            json_candidates.insert(0, array_match.group(0))

        for candidate in json_candidates:
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue

            raw_items = None
            if isinstance(parsed, list):
                raw_items = parsed
            elif isinstance(parsed, dict):
                for key in ("options", "player_options", "choices"):
                    value = parsed.get(key)
                    if isinstance(value, list):
                        raw_items = value
                        break

            if isinstance(raw_items, list):
                _append_options(raw_items)
                if len(options) >= 3:
                    return options[:3]

        # 兼容普通分行文本
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        _append_options(lines)

        # 不足时补默认选项
        defaults = ["我明白了", "继续", "好的"]
        for default_text in defaults:
            if len(options) >= 3:
                break
            if default_text not in options:
                options.append(default_text)

        return options[:3]
    
    def _ensure_dialogue_unique(self, dialogue: str, previous_dialogues: List[str], dialogue_round: int) -> str:
        """确保对话与之前的对话不重复，如果重复则调整"""
        if not previous_dialogues:
            return dialogue
        
        dialogue_lower = dialogue.lower().strip()
        
        # 检查是否与之前的对话重复
        for prev_dialogue in previous_dialogues:
            prev_lower = prev_dialogue.lower().strip()
            
            # 完全相同
            if dialogue_lower == prev_lower:
                # 如果是重复，根据轮次生成不同的内容
                if dialogue_round == 1:
                    return dialogue + "（开场）"
                elif dialogue_round == 2:
                    return dialogue + "（继续）"
                elif dialogue_round == 3:
                    return dialogue + "（深入）"
                else:
                    return dialogue + "（结尾）"
            
            # 高度相似（超过75%）
            similarity = self._calculate_similarity(dialogue_lower, prev_lower)
            if similarity > 0.75:
                # 如果相似度过高，尝试调整
                # 添加一些变化
                if dialogue_round <= 2:
                    return dialogue + "，你觉得呢？"
                else:
                    return dialogue + "，我们继续吧。"
        
        return dialogue
    
    def _filter_duplicate_options(self, options: List[str], character_dialogue: str) -> List[str]:
        """过滤掉与角色对话重复的选项（更严格的隔离）"""
        if not character_dialogue:
            return options
        
        filtered = []
        character_dialogue_lower = character_dialogue.lower().strip()
        character_words = set(character_dialogue_lower.split())
        
        for option in options:
            option_lower = option.lower().strip()
            
            # 检查是否与角色对话重复（更严格的检查）
            # 1. 完全相同的文本
            if option_lower == character_dialogue_lower:
                continue
            
            # 2. 高度相似（降低阈值到70%，更严格）
            similarity = self._calculate_similarity(option_lower, character_dialogue_lower)
            if similarity > 0.7:
                continue
            
            # 3. 包含角色对话的主要内容（降低阈值到40%，更严格）
            if self._has_significant_overlap(option_lower, character_dialogue_lower, threshold=0.4):
                continue
            
            # 4. 检查是否包含角色对话中的关键短语（新增，更严格）
            if len(character_words) > 0:
                option_words = set(option_lower.split())
                # 如果选项中有超过30%的词汇来自角色对话，则过滤
                common_words = option_words.intersection(character_words)
                if len(common_words) > 0 and len(common_words) / len(option_words) > 0.3:
                    continue
            
            # 5. 检查是否以相同的方式开头或结尾（新增）
            if len(character_dialogue_lower) > 5 and len(option_lower) > 5:
                # 检查前3个词或后3个词是否相同
                char_start = ' '.join(character_dialogue_lower.split()[:3])
                char_end = ' '.join(character_dialogue_lower.split()[-3:])
                option_start = ' '.join(option_lower.split()[:3])
                option_end = ' '.join(option_lower.split()[-3:])
                
                if option_start == char_start or option_end == char_end:
                    continue
            
            filtered.append(option)
        
        return filtered
    
    def _tokenize_text(self, text: str) -> set:
        """文本切分：兼容中文（字/双字gram）与英文单词。"""
        if not text:
            return set()

        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        if not normalized:
            return set()

        tokens = set()

        # 英文/数字 token
        for word in re.findall(r'[a-z0-9_]+', normalized):
            if len(word) > 1:
                tokens.add(word)

        # 中文 token：整段、单字、双字 gram
        for chunk in re.findall(r'[\u4e00-\u9fff]+', normalized):
            if not chunk:
                continue
            tokens.add(chunk)
            for ch in chunk:
                tokens.add(ch)
            if len(chunk) >= 2:
                for i in range(len(chunk) - 1):
                    tokens.add(chunk[i:i + 2])

        # 兜底空格分词
        for part in normalized.split():
            if len(part) > 1:
                tokens.add(part)

        return tokens

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本相似度（Jaccard）。"""
        words1 = self._tokenize_text(text1)
        words2 = self._tokenize_text(text2)

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        if not union:
            return 0.0

        return len(intersection) / len(union)
    
    def _has_significant_overlap(self, text1: str, text2: str, threshold: float = 0.5) -> bool:
        """检查两个文本是否有显著重叠（默认超过50%的词汇相同，可调整阈值）"""
        words1 = self._tokenize_text(text1)
        words2 = self._tokenize_text(text2)
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        min_len = min(len(words1), len(words2))
        
        if min_len == 0:
            return False
        
        overlap_ratio = len(intersection) / min_len
        return overlap_ratio > threshold
    
    def _supplement_options(self, options: List[str], character_dialogue: str, 
                           story_background: str, previous_dialogues: List[str]) -> List[str]:
        """补充选项，确保有3个不重复的选项"""
        # 如果选项不足，生成补充选项
        needed = 3 - len(options)
        
        if needed <= 0:
            return options
        
        # 生成补充选项的提示词
        previous_context = "\n".join(previous_dialogues[-2:]) if previous_dialogues else "这是第一轮对话。"
        
        supplement_prompt = f"""请生成{needed}个玩家回复选项，要求：
1. 每个选项10-25字
2. 必须回应角色的话："{character_dialogue}"
3. 必须基于故事背景：{story_background[:100]}
4. 必须考虑历史对话：{previous_context}
5. 【禁止】绝对不要重复角色说的话
6. 【禁止】绝对不要使用角色的表达方式
7. 【禁止】选项内容必须与角色对话完全不同
8. 【隔离】玩家选项和角色对话必须完全隔离
9. 只输出选项内容，每行一个

补充选项："""
        
        try:
            if self.enabled:
                result = self._call_text_generation(supplement_prompt, max_tokens=100, temperature=0.9)
                if result:
                    supplement_text = result.strip()
                    supplement_options = self._parse_options(supplement_text)
                    # 过滤重复
                    supplement_options = self._filter_duplicate_options(supplement_options, character_dialogue)
                    # 添加到现有选项
                    options.extend(supplement_options[:needed])
        except Exception as e:
            print(f"[警告] 补充选项生成失败: {e}")
        
        # 如果还是不足，使用默认选项
        while len(options) < 3:
            if len(options) == 0:
                options.append("我明白了")
            elif len(options) == 1:
                options.append("继续")
            else:
                options.append("好的")
        
        return options[:3]
    
    def _fallback_story(self, previous_events: List[str], current_context: str) -> str:
        """回退的故事生成"""
        if previous_events:
            return f"基于过往的经历，{previous_events[0][:200]}..."
        return f"这是一个新的开始。{current_context}"
    
    def _fallback_dialogue(self, character_info: Dict, state_values: Dict) -> str:
        """回退的对话生成"""
        personality = character_info.get('personality', '')
        favorability = state_values.get('favorability', 0)
        
        if favorability > 60:
            tone = "友好地"
        elif favorability < 20:
            tone = "冷淡地"
        else:
            tone = "平静地"
        
        return f"角色{tone}说道：\"...\""
    
    def _calculate_dynamic_state_changes(self, personality_dict: dict = None, 
                                        current_states: object = None, 
                                        option_type: str = 'increase') -> dict:
        """动态计算状态值变化（根据角色性格和当前情绪状态）
        
        Args:
            personality_dict: 角色性格字典（包含keywords等）
            current_states: 当前角色状态对象
            option_type: 选项类型（'increase'或'decrease'）
        
        Returns:
            状态值变化字典
        """
        import random
        
        # 基础影响值
        base_favorability = 5.0
        base_trust = 3.0
        base_happiness = 5.0
        base_emotion = 3.0
        
        # 根据角色性格调整影响值
        personality_keywords = []
        if personality_dict and isinstance(personality_dict, dict):
            personality_keywords = personality_dict.get('keywords', [])
        
        # 性格影响系数
        personality_multiplier = 1.0
        
        # 高冷性格：对积极选项反应较小，对消极选项反应较大
        if any('高冷' in kw or '冷淡' in kw or '冷漠' in kw for kw in personality_keywords):
            if option_type == 'increase':
                personality_multiplier = 0.7  # 高冷性格对积极选项反应较小
            else:
                personality_multiplier = 1.3  # 对消极选项反应较大
        
        # 热情性格：对积极选项反应较大，对消极选项反应较小
        elif any('热情' in kw or '开朗' in kw or '活泼' in kw for kw in personality_keywords):
            if option_type == 'increase':
                personality_multiplier = 1.3  # 热情性格对积极选项反应较大
            else:
                personality_multiplier = 0.7  # 对消极选项反应较小
        
        # 内向性格：所有反应都较小
        elif any('内向' in kw or '害羞' in kw or '腼腆' in kw for kw in personality_keywords):
            personality_multiplier = 0.8
        
        # 外向性格：所有反应都较大
        elif any('外向' in kw or '健谈' in kw or '社交' in kw for kw in personality_keywords):
            personality_multiplier = 1.2
        
        # 根据当前情绪状态调整影响值
        emotion_multiplier = 1.0
        if current_states:
            emotion = current_states.emotion
            
            # 情绪高涨时：对积极选项反应更大，对消极选项反应更小
            if emotion >= 70:
                if option_type == 'increase':
                    emotion_multiplier = 1.2
                else:
                    emotion_multiplier = 0.8
            
            # 情绪低落时：对积极选项反应更小，对消极选项反应更大
            elif emotion <= 30:
                if option_type == 'increase':
                    emotion_multiplier = 0.8
                else:
                    emotion_multiplier = 1.2
        
        # 计算最终影响值
        final_multiplier = personality_multiplier * emotion_multiplier
        
        if option_type == 'increase':
            return {
                'favorability': round(base_favorability * final_multiplier + random.uniform(-1, 1), 1),
                'trust': round(base_trust * final_multiplier + random.uniform(-0.5, 0.5), 1),
                'happiness': round(base_happiness * final_multiplier + random.uniform(-1, 1), 1),
                'emotion': round(base_emotion * final_multiplier + random.uniform(-0.5, 0.5), 1)
            }
        else:  # decrease
            return {
                'favorability': round(-base_favorability * final_multiplier + random.uniform(-1, 1), 1),
                'trust': round(-base_trust * final_multiplier + random.uniform(-0.5, 0.5), 1),
                'happiness': round(-base_happiness * final_multiplier + random.uniform(-1, 1), 1),
                'emotion': round(-base_emotion * final_multiplier + random.uniform(-0.5, 0.5), 1)
            }
    
    def _fallback_options(self) -> List[Dict]:
        """回退的选项生成"""
        import random
        return [
            {
                'id': 1,
                'text': '积极回应',
                'type': 'increase',
                'state_changes': {
                    'favorability': random.uniform(5, 15),
                    'trust': random.uniform(3, 10),
                    'happiness': random.uniform(5, 12)
                }
            },
            {
                'id': 2,
                'text': '保持距离',
                'type': 'neutral',
                'state_changes': {}
            },
            {
                'id': 3,
                'text': '消极回应',
                'type': 'decrease',
                'state_changes': {
                    'favorability': random.uniform(-10, -5),
                    'trust': random.uniform(-8, -3),
                    'happiness': random.uniform(-10, -5)
                }
            }
        ]
