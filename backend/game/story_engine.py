"""剧情推进引擎"""
import random
import os
import re
import time
from typing import Dict, List, Optional, Any
from data.scenes import (
    SCENES, 
    MAJOR_SCENES, 
    SUB_SCENES,
    get_sub_scenes_by_major_scene,
    get_major_scene_by_sub_scene,
    get_major_scene_keyword
)
from game.event_generator import EventGenerator
from database.db_manager import DatabaseManager
import config


class StoryEngine:
    """剧情推进引擎"""
    
    def __init__(self, event_generator: EventGenerator, db_manager: DatabaseManager):
        self.event_generator = event_generator
        self.db_manager = db_manager
        self.current_event_count = 0
        self.current_event = None  # 当前事件信息
        self.dialogue_history = []  # 当前事件的完整对话历史（包含角色对话和玩家选择）
        self.min_dialogue_rounds = 2  # 最少对话轮数（AI会决定是否继续）
        self.max_dialogue_rounds = 5  # 最多对话轮数（硬上限，避免事件对话过长）
        self.current_scene = 'classroom'  # 当前场景（小场景ID，默认使用教室）
        self.previous_event_contexts = []  # 记录之前的事件上下文，避免重复
    
    def _call_generation_with_retry(
        self, 
        model: str, 
        prompt: str, 
        max_tokens: int = 200, 
        temperature: float = 0.7,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[Any]:
        """带重试机制的文本生成调用（支持火山引擎和通义千问）
        
        Args:
            model: 模型名称（保留参数以兼容旧代码，实际使用AIGenerator的统一接口）
            prompt: 提示词
            max_tokens: 最大token数
            temperature: 温度参数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            响应对象（包含output.text属性），如果失败返回None
        """
        from game.ai_generator import AIGenerator
        
        ai_gen = AIGenerator()
        if not ai_gen.enabled:
            return None
        
        # 创建一个简单的响应对象包装类，兼容旧代码
        class ResponseWrapper:
            def __init__(self, text: str):
                class Output:
                    def __init__(self, text: str):
                        self.text = text
                self.output = Output(text)
                self.status_code = 200
        
        for attempt in range(max_retries):
            try:
                result = ai_gen._call_text_generation(prompt, max_tokens, temperature)
                if result:
                    return ResponseWrapper(result)
                else:
                    # 如果是账户错误，不重试
                    if attempt == 0:
                        print(f"[警告] 文本生成失败，将使用规则生成")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))  # 指数退避
                        continue
                    return None
                    
            except Exception as e:
                error_msg = str(e)
                # 检查是否是SSL错误或网络错误
                is_retryable = any(keyword in error_msg.lower() for keyword in [
                    'ssl', 'eof', 'connection', 'timeout', 'retry', 'network'
                ])
                
                if is_retryable and attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[警告] 文本生成失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                    print(f"[重试] {wait_time:.1f}秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[错误] 文本生成失败: {error_msg}")
                    import traceback
                    print(traceback.format_exc())
                    return None
        
        return None

    def _flatten_documents(self, documents) -> List[str]:
        """将ChromaDB query返回的documents统一拍平成 List[str]
        
        ChromaDB在query_texts为list时，返回格式通常是 List[List[str]]。
        这里统一做兼容：List[str] / List[List[str]] / 其他类型都尽量转成字符串列表。
        """
        if not documents:
            return []
        flattened: List[str] = []
        for item in documents:
            if item is None:
                continue
            if isinstance(item, list):
                for sub in item:
                    if sub is None:
                        continue
                    flattened.append(str(sub))
            else:
                flattened.append(str(item))
        return flattened
    
    def get_opening_event(self, character_id: int, scene_id: str = 'school', opening_event_id: Optional[str] = None) -> Dict:
        """获取开头事件（可指定事件ID，否则随机抽取）
        
        Args:
            character_id: 角色ID
            scene_id: 大场景ID（如'school'），用于获取该大场景下的初遇事件
            opening_event_id: 初遇事件ID（可选，如果不提供则随机选择）
        """
        # scene_id现在是大场景ID，从大场景获取初遇事件
        major_scene = MAJOR_SCENES.get(scene_id)
        if not major_scene:
            raise ValueError(f"大场景 {scene_id} 不存在")
        
        # 从大场景获取初遇事件列表
        opening_events = major_scene.get('opening_events', [])
        
        if not opening_events:
            # 如果没有定义初遇事件，从该大场景的小场景中随机选择一个，创建默认事件
            sub_scenes = major_scene.get('sub_scenes', [])
            if sub_scenes:
                random_sub_scene = random.choice(sub_scenes)
                sub_scene_info = SUB_SCENES.get(random_sub_scene, {})
                opening_events = [{
                    'id': f'{random_sub_scene}_meet',
                    'title': f'在{sub_scene_info.get("name", random_sub_scene)}初遇',
                    'description': f'在{sub_scene_info.get("name", random_sub_scene)}中，你们第一次相遇',
                    'sub_scene': random_sub_scene
                }]
            else:
                raise ValueError(f"大场景 {scene_id} 没有小场景")
        
        # 如果指定了事件ID，查找对应的事件；否则随机选择
        if opening_event_id:
            selected_event = None
            for event in opening_events:
                if event.get('id') == opening_event_id:
                    selected_event = event
                    break
            if not selected_event:
                raise ValueError(f"初遇事件 {opening_event_id} 在大场景 {scene_id} 中不存在")
            print(f"[故事引擎] 使用指定的初遇事件: {opening_event_id}")
        else:
            selected_event = random.choice(opening_events)
            print(f"[故事引擎] 随机选择初遇事件: {selected_event.get('id')}")
        
        # 获取事件对应的小场景ID（用于游戏）
        event_sub_scene_id = selected_event.get('sub_scene')
        if not event_sub_scene_id:
            # 如果事件没有指定sub_scene，尝试从事件ID推断
            event_id = selected_event['id']
            if event_id in SUB_SCENES:
                event_sub_scene_id = event_id
            else:
                # 从大场景的小场景中随机选择一个
                sub_scenes = major_scene.get('sub_scenes', [])
                if sub_scenes:
                    event_sub_scene_id = random.choice(sub_scenes)
                else:
                    raise ValueError(f"无法确定事件对应的小场景")
        
        # 生成事件（包含故事背景）
        event = self.event_generator.generate_event(
            character_id=character_id,
            event_id=selected_event['id'],
            event_context=selected_event['description'],
            previous_contexts=self.previous_event_contexts
        )
        
        event['title'] = selected_event['title']
        event['event_context'] = selected_event['description']
        event['scene'] = event_sub_scene_id  # 使用小场景ID
        event['major_scene'] = scene_id  # 保存大场景ID
        self.current_event_count = 1
        self.current_event = event
        self.dialogue_history = []  # 重置对话历史
        
        # 更新当前场景为事件对应的小场景
        self.current_scene = event_sub_scene_id
        print(f"[初遇事件] 大场景: {MAJOR_SCENES.get(scene_id, {}).get('name', scene_id)}, 小场景: {SUB_SCENES.get(event_sub_scene_id, {}).get('name', event_sub_scene_id)}")
        
        return event
    
    def get_middle_event(self, character_id: int, event_number: int) -> Dict:
        """获取中间事件（重构版：通过检索向量数据库历史事件来推演故事背景）
        
        历史事件包括：故事背景文本、角色文本、玩家选项文本
        """
        # 从向量数据库检索历史事件（包括故事背景文本、角色文本、玩家选项文本）
        # 用于推演后续事件的故事背景
        # 统一使用 search_similar_events 检索，确保能获取到完整的历史事件内容
        previous_events = self.event_generator.vector_db.search_similar_events(
            character_id=character_id,
            query="故事背景 角色文本 玩家选项 剧情发展 事件 对话",  # 检索完整的历史事件
            n_results=15  # 增加检索数量，获取更多历史信息
        )
        previous_docs = self._flatten_documents(previous_events.get('documents', []))
        
        # 如果检索结果为空，尝试使用更宽泛的查询
        if not previous_docs and event_number == 1:
            # 第1个中间事件：如果语义搜索失败，尝试检索最近的对话
            previous_dialogues = self.event_generator.vector_db.search_recent_dialogues(
                character_id=character_id,
                event_id=self.current_event['event_id'] if self.current_event else None,
                n_results=10
            )
            previous_docs = self._flatten_documents(previous_dialogues.get('documents', []))
        
        # 2. 从历史事件中提取场景关键词，推演下一个场景
        next_scene = self._infer_next_scene_from_history(
            character_id=character_id,
            previous_events=previous_docs,
            current_scene=self.current_scene
        )
        
        # 生成事件上下文（由AI基于历史事件生成，确保不重复且有连续性）
        event_context = self._generate_event_context(
            character_id=character_id,
            event_number=event_number,
            previous_events=previous_docs,
            current_scene=next_scene
        )
        
        # 更新当前场景
        if next_scene != self.current_scene:
            scene_name = SCENES.get(next_scene, {}).get('name', next_scene)
            print(f"[场景切换] 从 {SCENES.get(self.current_scene, {}).get('name', self.current_scene)} 切换到 {scene_name}")
            self.current_scene = next_scene
            
            # 场景切换时生成场景图片并合成
            try:
                from api.services.image_service import ImageService
                image_service = ImageService()
                if image_service.enabled:
                    scene_info = SCENES.get(next_scene, {})
                    scene_data = {
                        'scene_id': next_scene,
                        'scene_name': scene_info.get('name', next_scene),
                        'scene_description': scene_info.get('description', '')
                    }
                    print(f"[场景切换] 正在生成场景图片: {scene_name}")
                    scene_image_url = image_service.generate_scene_image(scene_data, next_scene)
                    if scene_image_url:
                        print(f"[场景切换] 场景图片生成成功: {scene_image_url}")
                        
                        # 尝试合成场景图和人物图
                        try:
                            # 获取角色最新的图片路径
                            character_image_path = image_service.get_latest_character_image_path(character_id)
                            if character_image_path:
                                print(f"[场景切换] 找到角色图片: {character_image_path}")
                                
                                # 获取场景图片路径（优先使用本地保存的路径）
                                scene_image_path = image_service.get_latest_scene_image_path(next_scene)
                                if not scene_image_path:
                                    # 如果本地没有，使用URL（会先下载）
                                    scene_image_path = scene_image_url
                                
                                # 合成图片
                                print(f"[场景切换] 正在合成场景图和人物图...")
                                composite_path = image_service.composite_scene_with_character(
                                    scene_image_path=scene_image_path,
                                    character_image_path=character_image_path,
                                    character_id=character_id,
                                    scene_id=next_scene,
                                    user_id=None  # 可以从session中获取user_id
                                )
                                
                                if composite_path and os.path.exists(composite_path):
                                    # 构建静态文件URL（URL编码文件名）
                                    from urllib.parse import quote
                                    filename = os.path.basename(composite_path)
                                    encoded_filename = quote(filename, safe='')
                                    composite_url = f"/static/images/composite/{encoded_filename}"
                                    print(f"[场景切换] 合成图片成功: {composite_path} -> {composite_url}")
                                else:
                                    print(f"[场景切换] 合成图片失败")
                            else:
                                print(f"[场景切换] 未找到角色图片，跳过合成")
                        except Exception as e:
                            print(f"[警告] 图片合成过程出错: {e}")
                            import traceback
                            print(traceback.format_exc())
                    else:
                        print(f"[场景切换] 场景图片生成失败或未启用")
            except Exception as e:
                print(f"[警告] 场景切换时生成图片失败: {e}")
                import traceback
                print(traceback.format_exc())
        
        event_id = f"middle_event_{event_number}"
        
        event = self.event_generator.generate_event(
            character_id=character_id,
            event_id=event_id,
            event_context=event_context,
            previous_contexts=self.previous_event_contexts
        )
        
        event['title'] = f"事件 {event_number}"
        event['event_context'] = event_context
        event['scene'] = self.current_scene
        self.current_event_count = event_number + 1
        self.current_event = event
        self.dialogue_history = []  # 重置对话历史
        # 记录事件上下文摘要，避免重复（记录更长的摘要）
        self.previous_event_contexts.append(event_context[:150])
        # 只保留最近10个事件上下文，避免列表过长
        if len(self.previous_event_contexts) > 10:
            self.previous_event_contexts = self.previous_event_contexts[-10:]
        
        # 输出新事件信息
        scene_name = SCENES.get(self.current_scene, {}).get('name', self.current_scene)
        print(f"\n[新事件] 事件 {event_number} 开始")
        print(f"  - 场景: {scene_name} ({self.current_scene})")
        print(f"  - 事件上下文: {event_context[:150]}{'...' if len(event_context) > 150 else ''}")
        if event.get('story_background'):
            print(f"  - 故事背景: {event.get('story_background')[:150]}{'...' if len(event.get('story_background', '')) > 150 else ''}\n")
        
        return event
    
    def _generate_event_context(self, character_id: int, event_number: int, 
                                previous_events: List[str], current_scene: str) -> str:
        """生成事件上下文（使用AI，必须基于向量数据库检索的历史事件推演）
        
        Args:
            character_id: 角色ID
            event_number: 事件序号
            previous_events: 从向量数据库检索的历史事件列表（必须提供）
            current_scene: 当前场景
        """
        # 兜底：防御性拍平（避免调用方传入嵌套结构导致崩溃）
        previous_events = self._flatten_documents(previous_events)

        # 【重要】如果没有历史事件，必须从向量数据库检索
        if not previous_events:
            print("[警告] _generate_event_context未提供历史事件，从向量数据库检索...")
            # 从向量数据库检索历史事件
            search_results = self.event_generator.vector_db.search_similar_events(
                character_id=character_id,
                query="剧情 事件 场景 对话",
                n_results=10
            )
            if search_results.get('documents'):
                previous_events = self._flatten_documents(search_results['documents'])
            else:
                previous_events = []
        
        # 构建历史事件摘要（必须基于向量数据库检索）
        history_summary = ""
        if previous_events:
            history_summary = "\n".join([f"- {event[:200]}" for event in previous_events[:5]])  # 增加历史事件数量
        else:
            history_summary = "这是第一个中间事件，没有历史事件可参考。"
        
        # 获取场景描述（使用小场景）
        scene_info = SUB_SCENES.get(current_scene, {})
        scene_name = scene_info.get('name', current_scene)
        scene_desc = scene_info.get('description', f'在{scene_name}的场景中')
        
        # 获取大场景信息（用于生成关键词）
        major_scene_id = get_major_scene_by_sub_scene(current_scene)
        major_scene_info = MAJOR_SCENES.get(major_scene_id, {})
        major_scene_keyword = major_scene_info.get('keyword', '')
        
        # 构建已发生的事件摘要（避免重复）
        previous_summary = ""
        if self.previous_event_contexts:
            previous_summary = "\n已发生的事件摘要（不要重复）：\n" + "\n".join([f"- {ctx[:100]}" for ctx in self.previous_event_contexts[-5:]])
        
        # 判断剧情发展阶段（基于事件序号）
        if event_number <= 2:
            stage = "初期"
            stage_guidance = "这是剧情初期，事件应该比较自然、日常，可以是简单的互动、偶遇、或者因为学习、生活而产生的接触。不要过于戏剧化，保持真实感。"
        elif event_number <= 5:
            stage = "发展期"
            stage_guidance = "这是剧情发展期，可以开始有一些更深入的互动，比如一起学习、一起吃饭、一起参加活动等。关系在慢慢熟悉，但还不要过于亲密。"
        else:
            stage = "深入期"
            stage_guidance = "这是剧情深入期，可以有一些更私人的互动，比如分享心事、一起散步、互相帮助等。关系在逐渐加深，但要根据历史事件自然发展。"
        
        # 获取角色名称
        character = self.db_manager.get_character(character_id)
        character_name = character.name if character else "角色"
        
        # 使用AI生成事件上下文（必须基于向量数据库检索的历史事件）
        prompt = f"""你是一个剧情游戏的事件上下文生成器。请根据以下信息生成一个事件描述（40-60字）：

【重要】必须基于历史事件生成，不能脱离历史事件凭空创造！
【时间设定】故事发生在当下（现代），禁止出现“20世纪初/古代/民国/未来”等年代背景。

【历史事件】（从向量数据库检索，必须参考，确保连续性）：
{history_summary}
{previous_summary}

【角色信息】：
- 玩家：player
- 角色：{character_name}

【当前场景】：
{scene_name}（{current_scene}）
场景描述：{scene_desc}
大场景关键词：{major_scene_keyword}

【剧情阶段】：
当前是第{event_number}个中间事件，属于{stage}阶段。
{stage_guidance}

要求（按重要性排序）：
1. 【必须基于历史】必须基于历史事件自然推演，不能脱离历史事件。如果历史事件中没有相关内容，不能凭空创造。
2. 【循序渐进】关系发展要符合逻辑，一步步来。如果之前只是点头之交，现在不能突然变成亲密关系。
3. 【连续性】新事件必须与历史事件有明确的因果关系或时间顺序。如果历史事件中提到"明天一起去图书馆"，那么这次事件就可以在图书馆发生。
4. 【明确标识】在描述中明确使用"player"和"{character_name}"来标识玩家和角色，例如："player和{character_name}在图书馆相遇..."
5. 【合理性】事件要符合学生日常生活的逻辑。不要出现过于戏剧化、不切实际的情节。
6. 【具体情境】描述一个具体、真实的事件情境，包含具体的动作和场景细节。例如："在图书馆，player和{character_name}坐在同一张桌子学习，{character_name}主动问player一道数学题"。
7. 【自然过渡】如果场景切换了，要有合理的理由。例如：历史事件中提到"一起去咖啡厅"，那么这次就可以在咖啡厅。
8. 【适度推进】事件要有进展，但不能太快。初期保持日常互动，中期可以加深了解，后期才能有更深入的交流。
9. 【场景明确】明确描述当前场景，让玩家知道在哪里，发生了什么。
10. 【避免重复】不要重复之前已经发生过的具体事件，但可以在同一场景发生不同的事件。
11. 【第三人称】使用第三人称描述，明确区分player和{character_name}。
12. 只描述事件情境和具体动作，不要包含对话内容。
13. 【当下语境】用当代校园语境与生活细节（如作业、社团、手机消息、课程安排），不要出现年代错位的道具与社会背景。

事件描述："""
        
        try:
            from game.ai_generator import AIGenerator
            ai_gen = AIGenerator()
            if ai_gen.enabled:
                response = self._call_generation_with_retry(
                    model=None,  # 不再需要，使用AIGenerator的统一接口
                    prompt=prompt,
                    max_tokens=100,  # 优化：从200降到100，减少生成时间
                    temperature=0.7,  # 降低温度，让生成更稳定、更符合逻辑
                    max_retries=3,
                    retry_delay=1.0
                )
                
                if response:
                    context = response.output.text.strip()
                    # 清理可能的引号
                    context = context.strip('"').strip("'").strip()
                    return context
        except Exception as e:
            print(f"[警告] AI生成事件上下文失败: {e}")
        
        # 回退到规则生成
        return f"在{scene_name}，剧情继续发展..."
    
    def _infer_next_scene_from_history(
        self, 
        character_id: int, 
        previous_events: List[str], 
        current_scene: str
    ) -> str:
        """从历史事件中推演下一个场景
        
        逻辑：
        1. 从向量数据库的历史事件中提取场景相关的关键词（如"咖啡厅"、"教室"等）
        2. 使用AI分析历史事件，提取提到的场景
        3. 根据提取的场景关键词匹配对应的小场景
        4. 如果匹配不到，从当前大场景的小场景列表中随机选择
        """
        # 获取当前场景所属的大场景
        current_major_scene = get_major_scene_by_sub_scene(current_scene)
        
        # 兜底：防御性拍平（避免调用方传入嵌套结构导致崩溃）
        previous_events = self._flatten_documents(previous_events)

        # 如果没有历史内容，从当前大场景的小场景中随机选择
        if not previous_events:
            sub_scenes = get_sub_scenes_by_major_scene(current_major_scene)
            if sub_scenes:
                # 优先选择与当前场景不同的小场景
                available_scenes = [s for s in sub_scenes if s != current_scene]
                if available_scenes:
                    return random.choice(available_scenes)
                else:
                    return current_scene
            return current_scene
        
        # 组合历史事件文本，用于AI分析
        history_text = "\n".join([str(event)[:300] for event in previous_events[:5]])  # 取最近5条，每条最多300字
        
        # 使用AI从历史事件中提取场景关键词
        try:
            from game.ai_generator import AIGenerator
            ai_gen = AIGenerator()
            if ai_gen.enabled:
                # 获取当前大场景的关键词
                major_scene_keyword = get_major_scene_keyword(current_major_scene)
                
                # 获取所有小场景的关键词列表
                all_sub_scenes_info = []
                for scene_id, scene_info in SUB_SCENES.items():
                    if scene_info.get('major_scene') == current_major_scene:
                        all_sub_scenes_info.append({
                            'id': scene_id,
                            'name': scene_info.get('name', ''),
                            'keywords': scene_info.get('keywords', '')
                        })
                
                sub_scenes_list = "\n".join([
                    f"- {info['name']} ({info['id']}): {info['keywords']}" 
                    for info in all_sub_scenes_info
                ])
                
                prompt = f"""你是一个场景推演助手。请根据历史事件和对话，分析下一个事件应该发生在哪个场景。

【历史事件和对话】：
{history_text}

【当前场景】：
{SUB_SCENES.get(current_scene, {}).get('name', current_scene)}

【可用的小场景列表】（属于"{MAJOR_SCENES.get(current_major_scene, {}).get('name', '学校')}"大场景）：
{sub_scenes_list}

【大场景关键词】：
{major_scene_keyword}

要求（按优先级）：
1. 【明确提及】如果历史事件中明确提到要去某个地方（如"去咖啡厅"、"到教室"、"在图书馆"、"明天一起去操场"等），必须选择该场景
2. 【暗示场景】如果历史事件中暗示了某个场景（如"聊到过几天要去咖啡厅喝咖啡"、"说好一起学习"暗示图书馆或自习室），选择该场景
3. 【自然过渡】如果没有明确提到，选择与当前场景有自然关联的场景。例如：从教室到图书馆（学习相关）、从教室到食堂（时间顺序）、从操场到体育馆（运动相关）
4. 【避免跳跃】不要选择与当前场景和剧情完全无关的场景，除非历史事件明确提到了
5. 【适度切换】如果当前场景刚使用过，且没有明确理由切换，可以保持当前场景（20%概率）
6. 【合理性】场景选择要符合学生日常生活的逻辑，不要出现不合理的场景切换

请只返回场景ID（如：library、classroom、cafeteria等），不要返回其他内容。如果无法确定，返回"random"让我随机选择。"""
                
                response = self._call_generation_with_retry(
                    model=None,  # 不再需要，使用AIGenerator的统一接口
                    prompt=prompt,
                    max_tokens=50,
                    temperature=0.5,  # 降低温度，让场景选择更准确、更符合逻辑
                    max_retries=3,
                    retry_delay=1.0
                )
                
                if response:
                    inferred_scene = response.output.text.strip()
                    # 清理可能的引号和其他字符
                    inferred_scene = inferred_scene.strip('"').strip("'").strip().strip('。').strip('，')
                    
                    # 检查是否是有效的场景ID
                    if inferred_scene in SUB_SCENES:
                        # 验证该场景属于当前大场景
                        if SUB_SCENES[inferred_scene].get('major_scene') == current_major_scene:
                            print(f"[场景推演] 从历史事件推演出场景: {SUB_SCENES[inferred_scene].get('name', inferred_scene)}")
                            return inferred_scene
                        else:
                            print(f"[场景推演] 推演的场景 {inferred_scene} 不属于当前大场景，使用备选方案")
                    elif inferred_scene.lower() == 'random':
                        print(f"[场景推演] AI返回random，使用随机选择")
                    else:
                        print(f"[场景推演] AI返回的场景ID无效: {inferred_scene}，使用备选方案")
        except Exception as e:
            print(f"[警告] AI推演场景失败: {e}")
            import traceback
            print(traceback.format_exc())
        
        # 备选方案1：从历史事件文本中直接匹配场景关键词
        matched_scene = self._match_scene_from_text(history_text, current_major_scene)
        if matched_scene:
            print(f"[场景推演] 通过关键词匹配到场景: {SUB_SCENES.get(matched_scene, {}).get('name', matched_scene)}")
            return matched_scene
        
        # 备选方案2：从当前大场景的小场景列表中随机选择
        sub_scenes = get_sub_scenes_by_major_scene(current_major_scene)
        if sub_scenes:
            # 70%概率切换场景，30%概率保持当前场景
            if random.random() < 0.7:
                available_scenes = [s for s in sub_scenes if s != current_scene]
                if available_scenes:
                    next_scene = random.choice(available_scenes)
                    print(f"[场景推演] 随机选择场景: {SUB_SCENES.get(next_scene, {}).get('name', next_scene)}")
                    return next_scene
        
        # 保持当前场景
        print(f"[场景推演] 保持当前场景: {SUB_SCENES.get(current_scene, {}).get('name', current_scene)}")
        return current_scene
    
    def _match_scene_from_text(self, text: str, major_scene: str) -> Optional[str]:
        """从文本中匹配场景关键词，返回匹配的场景ID"""
        if not text:
            return None
        
        # 获取该大场景下的所有小场景
        sub_scenes = get_sub_scenes_by_major_scene(major_scene)
        
        # 为每个小场景计算匹配分数
        scene_scores = {}
        for scene_id in sub_scenes:
            scene_info = SUB_SCENES.get(scene_id, {})
            keywords = scene_info.get('keywords', '').split()
            scene_name = scene_info.get('name', '')
            
            score = 0
            # 检查场景名称是否在文本中
            if scene_name in text:
                score += 10
            # 检查关键词是否在文本中
            for keyword in keywords:
                if keyword in text:
                    score += 2
            
            if score > 0:
                scene_scores[scene_id] = score
        
        # 返回得分最高的场景
        if scene_scores:
            best_scene = max(scene_scores, key=scene_scores.get)
            if scene_scores[best_scene] >= 5:  # 至少要有一定匹配度
                return best_scene
        
        return None
    
    def get_ending_event(self, character_id: int) -> Dict:
        """获取结尾事件（根据状态值判定）"""
        states = self.db_manager.get_character_states(character_id)
        attributes = self.db_manager.get_character_attributes(character_id)
        
        # 根据状态值判定结局类型
        favorability = states.favorability if states else 0.0
        trust = states.trust if states else 0.0
        hostility = states.hostility if states else 0.0
        
        # 判定结局
        if favorability > 70 and trust > 60 and hostility < 20:
            ending_type = "happy_ending"
            event_context = "经过一系列事件，你们的关系变得更加亲密，这是一个美好的结局。"
        elif favorability < 30 or hostility > 50:
            ending_type = "bad_ending"
            event_context = "关系走向了不好的方向，你们之间的距离越来越远。"
        elif trust > 50 and favorability > 40:
            ending_type = "neutral_ending"
            event_context = "你们的关系保持在一个稳定的状态，未来还有无限可能。"
        else:
            ending_type = "open_ending"
            event_context = "故事还在继续，结局尚未确定..."
        
        event = self.event_generator.generate_event(
            character_id=character_id,
            event_id=f"ending_{ending_type}",
            event_context=event_context
        )
        
        event['title'] = "结局"
        event['ending_type'] = ending_type
        event['event_context'] = event_context
        self.current_event = event
        self.dialogue_history = []  # 重置对话历史
        
        return event
    
    def record_character_dialogue(self, dialogue: str):
        """记录角色对话到对话历史"""
        if dialogue:
            self.dialogue_history.append({
                'type': 'character',
                'content': dialogue
            })
    
    def process_player_choice(self, character_id: int, choice: Dict):
        """处理玩家选择，更新状态值并记录对话历史"""
        # 记录玩家选择到对话历史
        if choice.get('text'):
            self.dialogue_history.append({
                'type': 'player',
                'content': choice['text']
            })
        
        # 更新状态值
        if choice['type'] != 'neutral' and choice.get('state_changes'):
            self.db_manager.update_character_states(
                character_id=character_id,
                state_changes=choice['state_changes']
            )
    
    def get_next_dialogue_round(self, character_id: int) -> Dict:
        """获取下一轮对话（角色对话 + 玩家选项）
        
        必须基于向量数据库检索的历史事件和对话来生成
        """
        if not self.current_event:
            raise ValueError("当前没有活动的事件")
        
        # 获取角色信息（用于名字标识）
        character = self.db_manager.get_character(character_id)
        character_name = character.name if character else "角色"
        
        # 计算当前对话轮次（每轮包含角色对话+玩家选择）
        dialogue_round = (len(self.dialogue_history) // 2) + 1
        
        # 【重要】从向量数据库检索历史事件和对话（用于推演）
        # 检索1：当前事件的最近对话
        recent_dialogues = self.event_generator.vector_db.search_recent_dialogues(
            character_id=character_id,
            event_id=self.current_event['event_id'],
            n_results=5
        )
        
        # 检索2：所有历史事件（用于连贯性）
        all_history_events = self.event_generator.vector_db.search_similar_events(
            character_id=character_id,
            query="对话 交流 谈话 剧情",
            n_results=10  # 检索更多历史事件
        )
        
        # 提取当前事件的对话内容（用于连贯性）
        previous_dialogues = []
        for item in self.dialogue_history:
            if item['type'] == 'character':
                # 确保格式包含角色名
                content = item['content']
                if not content.startswith(f"{character_name}:") and not content.startswith(f"{character_name}："):
                    previous_dialogues.append(f"{character_name}: {content}")
                else:
                    previous_dialogues.append(content)
            elif item['type'] == 'player':
                # 明确标注玩家发言，避免模型混淆角色与玩家语句
                content = item['content']
                # 如果包含player:前缀，去除它
                if content.startswith("player:") or content.startswith("player："):
                    content = re.sub(r'^player[：:]\s*', '', content)
                previous_dialogues.append(f"玩家: {content}")
        
        # 从向量数据库添加历史对话（必须基于这些生成）
        if recent_dialogues.get('documents') and len(recent_dialogues['documents']) > 0:
            # 将向量数据库中的对话内容也加入上下文
            vector_dialogues = recent_dialogues['documents'][:5]  # 增加数量
            previous_dialogues.extend([f"[历史对话] {d[:150]}" for d in vector_dialogues])
        
        # 从历史事件中添加对话内容
        if all_history_events.get('documents') and len(all_history_events['documents']) > 0:
            # 提取历史事件中的对话内容
            history_events = all_history_events['documents'][:5]
            previous_dialogues.extend([f"[历史事件] {d[:150]}" for d in history_events])
        
        # 生成对话轮次（必须基于向量数据库检索的历史对话）
        dialogue_data = self.event_generator.generate_dialogue_round(
            character_id=character_id,
            story_background=self.current_event['story_background'],
            dialogue_round=dialogue_round,
            previous_dialogues=previous_dialogues  # 包含从向量数据库检索的所有历史对话
        )
        
        return dialogue_data
    
    def should_continue_dialogue(self, character_id: int) -> bool:
        """判断是否应该继续对话（由AI决定，确保对话有头有尾）"""
        current_rounds = len(self.dialogue_history) // 2

        # 硬上限：最多5轮对话，直接结束
        if current_rounds >= self.max_dialogue_rounds:
            print(f"[对话判断] 达到最大轮次上限({self.max_dialogue_rounds})，强制结束对话")
            return False

        # 如果对话轮次少于最少轮数，必须继续对话
        if len(self.dialogue_history) < self.min_dialogue_rounds:
            return True
        
        # 使用AI判断是否应该继续对话
        # 基于当前对话历史、故事背景、事件上下文来判断
        try:
            from game.ai_generator import AIGenerator
            ai_gen = AIGenerator()
            if ai_gen.enabled:
                # 获取角色信息
                character = self.db_manager.get_character(character_id)
                character_name = character.name if character else "角色"
                
                # 构建当前对话摘要
                dialogue_summary = []
                for item in self.dialogue_history[-6:]:  # 取最近3轮对话
                    if item['type'] == 'character':
                        dialogue_summary.append(f"{character_name}: {item['content']}")
                    elif item['type'] == 'player':
                        # 明确标注玩家发言，避免模型混淆角色与玩家语句
                        content = item['content']
                        # 如果包含player:前缀，去除它
                        if content.startswith("player:") or content.startswith("player："):
                            content = re.sub(r'^player[：:]\s*', '', content)
                        dialogue_summary.append(f"玩家: {content}")
                
                dialogue_text = "\n".join(dialogue_summary)
                
                # 从向量数据库检索历史对话，用于判断
                recent_events = self.event_generator.vector_db.search_similar_events(
                    character_id=character_id,
                    query="对话 交流 谈话",
                    n_results=3
                )
                
                history_context = ""
                if recent_events.get('documents'):
                    history_context = "\n历史事件对话参考：\n" + "\n".join([f"- {d[:150]}" for d in recent_events['documents'][:2]])
                
                prompt = f"""你是一个剧情游戏的对话判断助手。请判断当前事件的对话是否应该继续。

【时间设定】故事发生在当下（现代），不要出现年代错位背景。

【当前事件背景】：
{self.current_event.get('story_background', '')[:200] if self.current_event else ''}

【当前对话历史】：
{dialogue_text}

{history_context}

【判断标准】：
1. 如果对话刚刚开始（少于2轮），必须继续
2. 如果对话已经完整地概述了当前事件，可以结束
3. 如果对话已经为下一轮事件做好了铺垫（承上启下），可以结束
4. 如果对话还在发展中，需要继续
5. 对话必须有头有尾，不能突然中断
6. 如果已经接近最大轮次（最多{self.max_dialogue_rounds}轮），优先收束对话

请只返回"继续"或"结束"，不要返回其他内容。"""
                
                response = self._call_generation_with_retry(
                    model=None,  # 不再需要，使用AIGenerator的统一接口
                    prompt=prompt,
                    max_tokens=20,
                    temperature=0.3,
                    max_retries=3,
                    retry_delay=1.0
                )
                
                if response:
                    result = response.output.text.strip().lower()
                    if "结束" in result or "stop" in result or "finish" in result:
                        print(f"[对话判断] AI判断：对话应该结束（已完成{len(self.dialogue_history)//2}轮）")
                        return False
                    else:
                        print(f"[对话判断] AI判断：对话应该继续（当前{len(self.dialogue_history)//2}轮）")
                        return True
        except Exception as e:
            print(f"[警告] AI判断对话是否继续失败: {e}")
            # 回退：如果对话轮次>=4，可以结束；否则继续
            if len(self.dialogue_history) >= 8:  # 4轮对话
                return False
        
        # 默认继续（保守策略）
        return True
    
    def save_dialogue_round_to_vector_db(self, character_id: int, dialogue_round: int, state_changes: dict = None):
        """将当前轮次的对话保存到向量数据库（重构版：支持四类文本存储）
        
        Args:
            character_id: 角色ID
            dialogue_round: 对话轮次
            state_changes: 玩家选项带来的状态值变化字典
        """
        if not self.current_event:
            return
        
        # 获取本轮对话内容
        character_dialogue = None
        player_choice = None
        
        # 从对话历史中提取本轮对话（最后两条应该是角色对话和玩家选择）
        if len(self.dialogue_history) >= 2:
            # 检查最后两条
            last_two = self.dialogue_history[-2:]
            for item in last_two:
                if item['type'] == 'character' and not character_dialogue:
                    character_dialogue = item['content']
                elif item['type'] == 'player' and not player_choice:
                    player_choice = item['content']
        
        # 获取角色当前状态值（用于存储）
        states = self.db_manager.get_character_states(character_id)
        
        # 如果找到了对话内容，保存到向量数据库（包含四类文本）
        if character_dialogue and player_choice:
            self.event_generator.vector_db.add_dialogue_round(
                character_id=character_id,
                event_id=self.current_event['event_id'],
                story_background=self.current_event['story_background'],
                dialogue_round=dialogue_round,
                character_dialogue=character_dialogue,
                player_choice=player_choice,
                metadata={
                    'event_context': self.current_event.get('event_context', ''),
                    'title': self.current_event.get('title', ''),
                    'scene': self.current_event.get('scene', '')
                },
                states=states,  # 传递角色状态值
                state_changes=state_changes  # 传递状态值变化
            )
    
    def save_event_to_vector_db(self, character_id: int):
        """将当前事件的所有对话保存到向量数据库（保留用于完整事件保存）"""
        if not self.current_event:
            return
        
        # 组合所有对话内容（包含角色对话和玩家选择）
        all_dialogues = []
        for item in self.dialogue_history:
            if item['type'] == 'character':
                all_dialogues.append(f"角色: {item['content']}")
            elif item['type'] == 'player':
                all_dialogues.append(f"玩家: {item['content']}")
        
        dialogue_text = "\n".join(all_dialogues) if all_dialogues else "无对话"
        
        # 保存到向量数据库（包含故事背景和完整对话）
        self.event_generator.vector_db.add_event(
            character_id=character_id,
            event_id=self.current_event['event_id'],
            story_text=self.current_event['story_background'],
            dialogue_text=dialogue_text,
            metadata={
                'event_context': self.current_event.get('event_context', ''),
                'dialogue_rounds': len([d for d in self.dialogue_history if d['type'] == 'player']),
                'title': self.current_event.get('title', ''),
                'type': 'complete_event'  # 标记为完整事件
            }
        )
    
    def get_next_event(self, character_id: int, scene_id: str = 'school') -> Dict:
        """获取下一个事件"""
        if self.current_event_count == 0:
            # 开头事件
            return self.get_opening_event(character_id, scene_id)
        elif self.current_event_count <= config.GAME_CONFIG['max_events']:
            # 中间事件（从1开始计数，因为开头事件是第0个）
            return self.get_middle_event(character_id, self.current_event_count)
        else:
            # 结尾事件
            return self.get_ending_event(character_id)
    
    def get_current_scene(self) -> str:
        """获取当前场景"""
        return self.current_scene
    
    def is_game_finished(self) -> bool:
        """判断游戏是否结束"""
        # 当完成中间事件后，下一次获取事件时就是结尾
        return self.current_event_count > config.GAME_CONFIG['max_events']

