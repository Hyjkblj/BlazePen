"""图片生成服务（负责调用AI模型生成图片）"""
from typing import Dict, Any, Optional, List
import sys
import os

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config
from utils.logger import get_logger
from utils.path_utils import get_static_url

logger = get_logger(__name__)

# 尝试导入依赖
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests未安装，火山引擎图片生成功能将不可用。请运行: pip install requests")

try:
    import dashscope
    from dashscope import ImageSynthesis
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logger.warning("dashscope未安装，通义万相图片生成功能将不可用。请运行: pip install dashscope")


class ImageGenerationService:
    """图片生成服务（负责调用AI模型生成图片）
    
    职责：
    - 生成角色图片prompt
    - 生成场景图片prompt
    - 调用AI模型生成图片（火山引擎、DashScope）
    - 支持组图生成（角色图片）
    """
    
    def __init__(self, storage_service=None):
        """初始化图片生成服务
        
        Args:
            storage_service: 图片存储服务实例（用于保存生成的图片）
        """
        self.enabled = False
        self.provider = None
        self.volcengine_api_url = None
        self.storage_service = storage_service
        
        # 优先检查火山引擎Seedream API
        volcengine_key = config.VOLCENGINE_ARK_API_KEY.strip() if config.VOLCENGINE_ARK_API_KEY else ''
        
        if REQUESTS_AVAILABLE and volcengine_key:
            # 根据region构建API端点
            region_map = {
                'cn-beijing': 'ark.cn-beijing.volces.com',
                'cn-north-1': 'ark.cn-beijing.volces.com',
            }
            host = region_map.get(config.VOLCENGINE_REGION, 'ark.cn-beijing.volces.com')
            self.volcengine_api_url = f"https://{host}/api/v3/images/generations"
            self.enabled = True
            self.provider = 'volcengine'
            logger.info(f"图片生成服务已启用 - 使用服务: 火山引擎Seedream (VolcEngine)")
            logger.debug(f"API端点: {self.volcengine_api_url}")
            logger.debug(f"模型: {config.VOLCENGINE_IMAGE_MODEL}")
        elif not REQUESTS_AVAILABLE:
            logger.warning("requests未安装，火山引擎图片生成功能不可用")
        elif not volcengine_key:
            logger.warning("未配置VOLCENGINE_ARK_API_KEY或值为空，火山引擎图片生成功能不可用")
        
        # 如果火山引擎不可用，检查通义万相
        if not self.enabled:
            if DASHSCOPE_AVAILABLE and config.DASHSCOPE_API_KEY:
                dashscope.api_key = config.DASHSCOPE_API_KEY
                self.enabled = True
                self.provider = 'dashscope'
                logger.info(f"图片生成服务已启用 - 使用服务: 通义万相 (DashScope)")
            else:
                if not DASHSCOPE_AVAILABLE:
                    logger.warning("dashscope未安装，通义万相图片生成功能不可用")
                elif not config.DASHSCOPE_API_KEY:
                    logger.warning("未配置DASHSCOPE_API_KEY，通义万相图片生成功能不可用")
        
        if not self.enabled:
            logger.warning("所有图片生成服务均不可用，请配置至少一个服务")
    
    def generate_character_image_prompt(self, request_data: Dict[str, Any], generate_group: bool = True, group_count: int = 3) -> str:
        """根据前端接收的人物设定数据生成完整的图片生成prompt
        
        Args:
            request_data: 前端发送的角色创建请求数据
            generate_group: 是否生成组图（默认：True）
            group_count: 组图数量（默认：3）
            
        Returns:
            专业的中文图片生成prompt（简洁描述性文本，适合豆包Seedream模型）
        """
        name = request_data.get('name', '角色')
        gender = request_data.get('gender', '')
        age = request_data.get('age')
        
        # 解析外观数据
        appearance = request_data.get('appearance', {})
        appearance_keywords = []
        height = None
        weight = None
        
        if isinstance(appearance, dict):
            keywords = appearance.get('keywords', [])
            if isinstance(keywords, list):
                appearance_keywords = keywords
            height = appearance.get('height')
            weight = appearance.get('weight')
        
        # 解析性格数据
        personality = request_data.get('personality', {})
        personality_keywords = []
        if isinstance(personality, dict):
            keywords = personality.get('keywords', [])
            if isinstance(keywords, list):
                personality_keywords = keywords
        
        # 解析背景数据
        background = request_data.get('background', {})
        background_style = ''
        if isinstance(background, dict):
            background_style = background.get('style', '')
        
        # 构建prompt描述部分（类似示例风格：简洁、专业、描述性）
        prompt_parts = []
        
        # 0. 角色设定（在提示词开头）
        role_prompt = "你是一位游戏开发人员，负责开发一款二次元无限流剧情游戏，你负责的工作是根据玩家的要求生成他们内心的男神or女神图片"
        prompt_parts.append(role_prompt)
        
        # 1. 角色基础特征描述
        character_desc_parts = []
        
        # 性别和年龄
        if gender == 'male':
            gender_desc = '男性'
        elif gender == 'female':
            gender_desc = '女性'
        else:
            gender_desc = ''
        
        if gender_desc:
            if age:
                character_desc_parts.append(f'{age}岁{gender_desc}角色')
            else:
                character_desc_parts.append(f'{gender_desc}角色')
        elif age:
            character_desc_parts.append(f'{age}岁角色')
        
        # 外观特征（自然描述）
        if appearance_keywords:
            # 将关键词转换为自然描述，限制数量避免过长
            appearance_desc = '，'.join(appearance_keywords[:4])
            character_desc_parts.append(appearance_desc)
        
        if height:
            character_desc_parts.append(f'身高{height}cm')
        if weight:
            character_desc_parts.append(f'体重{weight}kg')
        
        if character_desc_parts:
            prompt_parts.append('，'.join(character_desc_parts))
        
        # 2. 性格特征（影响表情和姿态）
        if personality_keywords:
            personality_desc = '、'.join(personality_keywords[:3])
            prompt_parts.append(f'性格{personality_desc}')
        
        # 3. 风格描述
        if background_style:
            prompt_parts.append(f'{background_style}风格')
        
        # 4. 图片质量和技术要求（二次元动漫风格）
        quality_parts = [
            '二次元动漫风格',
            '高质量立绘',
            '全身像',
            '细节丰富',
            '精美插画',
            '专业画质',
            '8k分辨率',
            '柔和光线',
            '细腻笔触',
            '纯白背景',
            '白色背景',
            'PNG格式'
        ]
        prompt_parts.extend(quality_parts)
        
        # 组合成完整的prompt（用逗号分隔，自然流畅的描述性文本）
        prompt = '，'.join(prompt_parts)
        
        return prompt

    def generate_training_character_portrait_prompt(
        self,
        request_data: Dict[str, Any],
        generate_group: bool = True,
        group_count: int = 2,
    ) -> str:
        """训练专用：抗战时期（1937-1945）人物立绘提示词（9:16）。

        设计目标（关键）：
        - 竖版 9:16 立绘（半身/全身），主体偏下，顶部留干净负空间用于 UI/标题
        - 环境深红暗红为主（烟火、火光、废墟），人物低饱和灰黑，肤色偏中性偏冷；强烈前后景色彩分离
        - 通过前端传入 identity/identity_code 自动选择身份、道具与服饰（战地记者/摄影记者/通信员等）
        - 避免现代元素、二次元夸张风、文字水印
        """

        def _norm_text(value: object) -> str:
            return str(value or "").strip()

        name = _norm_text(request_data.get("name")) or "记者"
        gender = _norm_text(request_data.get("gender")).lower()
        age = request_data.get("age")

        appearance = request_data.get("appearance") if isinstance(request_data.get("appearance"), dict) else {}
        personality = request_data.get("personality") if isinstance(request_data.get("personality"), dict) else {}
        background = request_data.get("background") if isinstance(request_data.get("background"), dict) else {}

        appearance_keywords = (
            appearance.get("keywords") if isinstance(appearance.get("keywords"), list) else []
        )
        personality_keywords = (
            personality.get("keywords") if isinstance(personality.get("keywords"), list) else []
        )

        identity = _norm_text(request_data.get("identity"))
        identity_code = _norm_text(request_data.get("identity_code"))
        identity_hint = (identity or identity_code).lower()

        gender_desc = "女性" if gender == "female" else "男性" if gender == "male" else ""
        age_desc = f"{age}岁" if isinstance(age, int) and age > 0 else ""

        # 基于身份的道具/服饰锚定（优先命中明确职业）
        role_label = "战地记者"
        props = "笔记本与钢笔"
        clothing = "旧式风衣/粗布外套/棉布衬衫，围巾或绑腿，磨损质感"
        armband = "袖章可写 PRESS（不渲染文字也可仅表现袖章形状）"

        if any(key in identity_hint for key in ["photo", "photograph", "摄影", "photographer", "photography"]):
            role_label = "摄影记者"
            props = "老式胶片相机（复古机身，避免现代相机logo）"
            clothing = "战地摄影师的旧式外套与背带，皮革相机带，磨损质感"
            armband = "袖章（PRESS 形状）"
        elif any(key in identity_hint for key in ["radio", "通信", "电台", "operator", "通讯", "telegraph"]):
            role_label = "通信员"
            props = "文件与无线电设备/耳机（旧式电台），避免现代对讲机造型"
            clothing = "通信员旧式军装外套/粗布外套，绑腿与工具包，磨损质感"
            armband = "袖章（单位标识形状，避免现代徽章细节）"
        elif any(key in identity_hint for key in ["intel", "情报", "联络", "agent", "spy"]):
            role_label = "情报联络员"
            props = "文件袋、密写本、钢笔（不出现现代手机）"
            clothing = "低调旧式风衣与围巾，深灰低饱和，磨损质感"
            armband = "可不使用袖章"

        background_style = _norm_text(background.get("style")) if isinstance(background, dict) else ""

        prompt_parts: list[str] = []

        # 先写硬约束（更容易被模型遵守）
        prompt_parts.append(
            "1937-1945 抗日战争时期，战时中国城市战场废墟，纪实现实主义，史诗级 AAA 写实电影海报质感"
        )
        prompt_parts.append("竖版 9:16 单人角色立绘（半身或全身），画面中只出现一个人物，主体位于画面下半部，地平线降低")
        prompt_parts.append(
            "顶部约 15-20% 必须留干净负空间（平滑烟雾/天空渐变，低对比低细节），顶部边缘不得有头部贴边"
        )
        if generate_group and int(group_count or 0) >= 2:
            prompt_parts.append(
                "一次生成两张同一角色的不同变体（外观一致、服饰一致、时代一致、风格一致、色彩分级一致）："
                "第一张为全身站姿立绘（正面或三分之二侧），第二张为半身近景立绘（更强调表情与道具）；"
                "两张都必须保持主体偏下、顶部留白"
            )

        # 人物与身份
        base_bits = [bit for bit in [age_desc, gender_desc, name] if bit]
        if base_bits:
            prompt_parts.append("人物：" + "，".join(base_bits))
        prompt_parts.append(f"角色身份：{role_label}")
        prompt_parts.append(f"道具：{props}")
        prompt_parts.append(f"服饰：{clothing}，{armband}")
        prompt_parts.append("表情：冷静坚定，微风吹乱头发与衣角，姿态克制")

        # 细节来自前端字段
        if appearance_keywords:
            prompt_parts.append(
                "外观细节："
                + "，".join([_norm_text(x) for x in appearance_keywords[:5] if _norm_text(x)])
            )
        if personality_keywords:
            prompt_parts.append(
                "气质："
                + "、".join([_norm_text(x) for x in personality_keywords[:4] if _norm_text(x)])
            )
        if background_style:
            prompt_parts.append(f"美术风格补充：{background_style}，但保持抗战年代纪实质感")

        # 环境与氛围（适配竖版：背景虚化/不抢人；严格单人，不出现其他人）
        prompt_parts.append(
            "背景：断壁残垣、燃烧废墟、浓密黑烟柱、飘散火星与余烬、强风撕裂的红旗（虚化），城市剪影；"
            "背景中不得出现任何其他人物或人群剪影"
        )
        prompt_parts.append("氛围：庄重克制、悲壮英雄气质，纪录片式真实感")

        # 色彩与光照（关键）
        prompt_parts.append(
            "色彩分级（关键）：环境/背景深红暗红为主（枣红、血红、焦炭黑），火光红雾与余烬微光；"
            "人物保持低饱和灰黑（灰烬灰、铁灰、炭灰），肤色中性偏冷，人物脸部与衣物禁止出现明显红/橙色溢光；"
            "必须强烈前后景色彩分离：红在环境，灰在人物"
        )
        prompt_parts.append("光照：电影级侧后方光，微弱轮廓光，体积雾，尘埃颗粒，景深明确")
        prompt_parts.append("质感：胶片颗粒、轻微划痕、旧照片纹理，烟尘与碎屑轻微运动模糊，超高细节")
        prompt_parts.append("无文字、无水印、无Logo、无字幕")

        # 负向约束（合并在一个prompt里，兼容你们当前只传prompt的调用方式）
        prompt_parts.append(
            "避免：人物皮肤过饱和红、红脸/橙色面部偏色、暖调美颜棚拍光、人物服装鲜艳高饱和、塑料皮肤/磨皮滤镜、"
            "二次元/卡通/chibi、赛博朋克霓虹/未来元素/科幻、现代建筑与现代武器、智能手机、现代相机logo、"
            "蓝天白云、顶部区域杂乱细节、主体过高或头顶贴边、扁平光、低细节、明显模糊、解剖错误、任何文字伪影、"
            "双人/多人、合影、群像、分屏拼图、拼接画面、画中画、重复人物、额外人物、路人"
        )

        return "，".join([part for part in prompt_parts if part])
    
    def generate_scene_image_prompt(self, scene_data: Dict[str, Any]) -> str:
        """根据场景数据生成完整的场景图片生成prompt
        
        Args:
            scene_data: 场景数据，包含：
                - scene_id: 场景ID（如'school', 'library'等）
                - scene_name: 场景名称（可选）
                - scene_description: 场景描述（可选）
                - atmosphere: 氛围描述（可选）
                - time_of_day: 时间（如'白天', '夜晚'等，可选）
                - weather: 天气（如'晴天', '雨天'等，可选）
            
        Returns:
            专业的中文场景图片生成prompt（格式：生成一个XXX场景图片 二次元写实画风 图中无人物）
        """
        explicit_prompt = str(scene_data.get('prompt') or '').strip()
        if explicit_prompt:
            return self._finalize_scene_prompt(self._sanitize_scene_prompt(explicit_prompt))

        scene_id = scene_data.get('scene_id', '')
        scene_name = scene_data.get('scene_name', '')
        scene_description = scene_data.get('scene_description', '')
        atmosphere = scene_data.get('atmosphere', '')
        time_of_day = scene_data.get('time_of_day', '')
        weather = scene_data.get('weather', '')
        
        # 如果没有提供场景名称，尝试从场景ID获取
        if not scene_name and scene_id:
            try:
                from data.scenes import SCENES
                scene_info = SCENES.get(scene_id, {})
                scene_name = scene_info.get('name', scene_id)
                if not scene_description:
                    scene_description = scene_info.get('description', '')
            except:
                scene_name = scene_id
        
        # 构建场景描述（优先使用场景名称，如果没有则使用场景描述）
        scene_desc = scene_name if scene_name else (scene_description if scene_description else scene_id)
        
        # 构建完整的prompt（按照用户要求的格式）
        prompt = f"生成一个{scene_desc}场景图片"
        
        # 添加时间和天气信息（如果有）
        additional_info = []
        if time_of_day:
            additional_info.append(time_of_day)
        if weather:
            additional_info.append(weather)
        if atmosphere:
            additional_info.append(f"氛围{atmosphere}")
        
        if additional_info:
            prompt += f"，{''.join(additional_info)}"
        
        # 添加固定的风格和要求
        prompt += "，二次元写实画风，图中无人物"
        
        return self._finalize_scene_prompt(prompt)

    def _sanitize_scene_prompt(self, prompt: str) -> str:
        """尽量移除会诱发“画中文字/标题”的提示语。

        说明：场景图是训练 UI 背景，不希望模型渲染任何文字。实际业务中上层 prompt
        可能包含“海报/标题/叠字”等表述，会显著提升生成文字的概率；这里做最小清理。
        """
        text = str(prompt or "").strip()
        if not text:
            return ""

        # 常见诱发词：海报/标题/叠字/字幕/标语/文字等（简单替换，避免过度改写语义）
        for token in [
            "用于标题",
            "标题叠字",
            "叠字",
            "标题",
            "字幕",
            "标语",
            "海报构图",
            "海报",
            "poster",
            "title",
            "text overlay",
        ]:
            text = text.replace(token, "")

        # 压缩多余空白与重复标点
        text = " ".join(text.split())
        text = text.replace("，，", "，").replace(",,", ",")
        return text.strip(" ，,")

    def _finalize_scene_prompt(self, prompt: str) -> str:
        """为所有场景图 prompt 追加强制禁字约束。"""
        base = str(prompt or "").strip()
        no_text = (
            "强约束：画面中不得出现任何可读文字/汉字/英文/数字；不得出现标题、字幕、标语、招牌字、报纸正文、海报文字；"
            "不得出现水印、Logo、UI 字样、边框文字；禁止生成任何文字伪影或乱码。"
        )
        style = "画面只做场景背景，不要生成海报版式、排版设计、版面留白用于叠字。"
        if not base:
            return f"{no_text}，{style}"
        return f"{base}，{no_text}，{style}"
    
    def generate_character_image(self, prompt: str, character_id: Optional[int] = None, 
                                 user_id: Optional[str] = None, image_type: str = 'portrait',
                                 generate_group: bool = True, group_count: int = 3) -> Optional[List[str]]:
        """生成角色图片（支持组图生成，供前端三选一）
        
        Args:
            prompt: 图片生成prompt
            character_id: 角色ID（可选，用于保存图片URL）
            user_id: 玩家ID（可选，用于文件命名）
            image_type: 图片类型（portrait=立绘, avatar=头像，默认：portrait）
            generate_group: 是否生成组图（默认：True，生成3张图片供前端选择）
            group_count: 组图数量（默认：3）
            
        Returns:
            图片URL列表（如果生成成功），否则返回None
        """
        if not self.enabled:
            logger.warning("图片生成服务未启用，无法生成图片")
            return None
        
        try:
            if self.provider == 'volcengine':
                # 使用火山引擎生成图片（支持组图）
                return self._generate_with_volcengine(prompt, character_id, user_id, image_type, generate_group, group_count)
            elif self.provider == 'dashscope':
                # 使用通义万相生成图片（暂不支持组图，生成单张）
                result = self._generate_with_dashscope(prompt, character_id, user_id, image_type)
                return [result] if result else None
            else:
                logger.warning(f"未知的图片生成服务提供商: {self.provider}")
                return None
        except Exception as e:
            logger.error(f"图片生成失败: {e}", exc_info=True)
            return None
    
    def generate_character_image_by_data(self, request_data: Dict[str, Any], character_id: Optional[int] = None,
                                         user_id: Optional[str] = None, image_type: str = 'portrait',
                                         generate_group: bool = True, group_count: int = 3) -> Optional[List[str]]:
        """根据角色数据生成人物图片（便捷方法，支持组图）
        
        Args:
            request_data: 前端发送的角色创建请求数据
            character_id: 角色ID（可选）
            user_id: 玩家ID（可选，用于文件命名）
            image_type: 图片类型（portrait=立绘, avatar=头像，默认：portrait）
            generate_group: 是否生成组图（默认：True，生成3张图片供前端选择）
            group_count: 组图数量（默认：3）
            
        Returns:
            图片URL列表，如果失败返回None
        """
        # 生成prompt
        # 训练人物立绘（preview-jobs）会带 identity_code；为其使用抗战时期风格的专用提示词生成器。
        if isinstance(request_data, dict) and str(request_data.get("identity_code") or "").strip():
            prompt = self.generate_training_character_portrait_prompt(request_data, generate_group, group_count)
        else:
            prompt = self.generate_character_image_prompt(request_data, generate_group, group_count)
        
        # 生成图片
        return self.generate_character_image(prompt, character_id, user_id, image_type, generate_group, group_count)
    
    def generate_scene_image(self, scene_data: Dict[str, Any], scene_id: Optional[str] = None,
                            user_id: Optional[str] = None) -> Optional[str]:
        """生成场景图片
        
        Args:
            scene_data: 场景数据（包含scene_id, scene_name, scene_description等）
            scene_id: 场景ID（可选，如果scene_data中没有提供）
            user_id: 玩家ID（可选，用于文件命名）
            
        Returns:
            图片URL，如果失败返回None
        """
        if not self.enabled:
            logger.warning("图片生成服务未启用，无法生成图片")
            return None
        
        # 确保scene_id存在
        if not scene_data.get('scene_id') and scene_id:
            scene_data['scene_id'] = scene_id
        
        # 生成场景图片prompt
        prompt = self.generate_scene_image_prompt(scene_data)
        
        # 获取场景信息用于文件命名
        scene_id_for_naming = scene_data.get('scene_id', scene_id or 'unknown')
        scene_name_for_naming = scene_data.get('scene_name', '')
        
        try:
            if self.provider == 'volcengine':
                # 使用火山引擎生成场景图片
                return self._generate_scene_with_volcengine(prompt, scene_id_for_naming, scene_name_for_naming, user_id)
            elif self.provider == 'dashscope':
                # 使用通义万相生成场景图片
                return self._generate_scene_with_dashscope(prompt, scene_id_for_naming, scene_name_for_naming, user_id)
            else:
                logger.warning(f"未知的图片生成服务提供商: {self.provider}")
                return None
        except Exception as e:
            logger.error(f"场景图片生成失败: {e}", exc_info=True)
            return None
    
    def _generate_with_volcengine(self, prompt: str, character_id: Optional[int] = None,
                                  user_id: Optional[str] = None, image_type: str = 'portrait',
                                  generate_group: bool = True, group_count: int = 3) -> Optional[List[str]]:
        """使用火山引擎Seedream 4.0-4.5 API生成图片（支持组图）
        
        Args:
            prompt: 图片生成prompt（基础prompt，会根据组图需求添加变体）
            character_id: 角色ID（可选）
            user_id: 玩家ID（可选，用于文件命名）
            image_type: 图片类型（portrait=立绘, avatar=头像）
            generate_group: 是否生成组图（默认：True）
            group_count: 组图数量（默认：3）
            
        Returns:
            图片URL列表，如果失败返回None
        """
        try:
            if generate_group:
                logger.info(f"正在使用火山引擎Seedream生成角色组图 (角色ID: {character_id}, 数量: {group_count}, 比例: 9:16, 无水印)")
                logger.debug(f"将调用 {group_count} 次API生成 {group_count} 张不同变体的图片")
            else:
                logger.info(f"正在使用火山引擎Seedream生成角色图片 (角色ID: {character_id}, 比例: 9:16, 无水印)")
            logger.debug(f"基础Prompt: {prompt[:100]}...")
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {config.VOLCENGINE_ARK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # 人物图片使用9:16竖屏比例（适合人物立绘）
            character_image_size = "1440x2560"  # 9:16竖屏比例，2K分辨率
            
            # 预览图（1-2张）改为单次请求异步任务内生成，避免“组图=多次请求+变体prompt”的方式
            if generate_group and group_count > 1:
                logger.info(
                    f"正在使用火山引擎Seedream生成角色预览图 (角色ID: {character_id}, 数量: {group_count}, 比例: 9:16, 无水印)"
                )
                def _request_one(*, request_prompt: str) -> str | None:
                    payload = {
                        "model": config.VOLCENGINE_IMAGE_MODEL,
                        "prompt": request_prompt,
                        "size": character_image_size,
                        "response_format": "url",
                        "watermark": False,
                    }

                    response = requests.post(
                        self.volcengine_api_url,
                        headers=headers,
                        json=payload,
                        timeout=180,
                    )

                    if response.status_code != 200:
                        logger.warning(f"火山引擎API请求失败: HTTP {response.status_code}")
                        try:
                            resp_preview = response.text[:800]
                        except Exception:
                            resp_preview = "<unreadable response body>"
                        logger.warning(
                            "火山引擎图片生成HTTP失败: model=%s size=%s status=%s body=%s",
                            payload.get("model"),
                            payload.get("size"),
                            response.status_code,
                            resp_preview,
                        )
                        return None

                    try:
                        resp_data = response.json()
                    except Exception:
                        logger.warning(
                            "火山引擎图片生成响应不是JSON: model=%s size=%s status=%s body=%s",
                            payload.get("model"),
                            payload.get("size"),
                            response.status_code,
                            response.text[:800] if hasattr(response, "text") else "<no body>",
                        )
                        return None

                    if 'error' in resp_data:
                        error_info = resp_data['error']
                        error_msg = error_info.get('message', '未知错误')
                        error_code = error_info.get('code') or error_info.get('type') or None
                        logger.warning(f"火山引擎图片生成失败: {error_msg}")
                        logger.warning(
                            "火山引擎图片生成返回error: model=%s size=%s code=%s message=%s",
                            payload.get("model"),
                            payload.get("size"),
                            error_code,
                            error_msg,
                        )
                        return None

                    data = resp_data.get('data')
                    if not isinstance(data, list) or len(data) == 0:
                        logger.warning(f"响应中未找到data字段或data为空: {resp_data}")
                        return None

                    first = data[0] if isinstance(data[0], dict) else None
                    if not first:
                        return None
                    image_url = first.get('url')
                    return str(image_url).strip() if image_url else None

                # 一次要 2 张：并发异步调用两次（每次生成 1 张），避免依赖模型对 n 参数的支持。
                # 两次请求用轻微变体（全身/半身），但必须保持同一角色一致性。
                from concurrent.futures import ThreadPoolExecutor

                target_count = int(group_count)
                target_count = 2 if target_count >= 2 else 1
                prompt_full = f"{prompt}，变体A：全身站姿立绘，背景更虚化，仍保持单人且顶部留白"
                prompt_close = f"{prompt}，变体B：半身近景立绘，强调表情与道具，背景更虚化，仍保持单人且顶部留白"

                raw_urls: list[str] = []
                with ThreadPoolExecutor(max_workers=2) as request_pool:
                    futures = [
                        request_pool.submit(_request_one, request_prompt=prompt_full),
                        request_pool.submit(_request_one, request_prompt=prompt_close),
                    ]
                    for fut in futures:
                        try:
                            url = fut.result(timeout=200)
                        except Exception:
                            url = None
                        if url:
                            raw_urls.append(url)

                # 若仍不足 2 张，补一次单请求兜底（最多补 1 张）
                if target_count == 2 and len(raw_urls) < 2:
                    fallback_url = _request_one(
                        request_prompt=f"{prompt}，补充兜底：全身或半身皆可，保持单人且顶部留白，风格一致"
                    )
                    if fallback_url:
                        raw_urls.append(fallback_url)

                # 去重并落盘（最多取 target_count）
                image_urls: List[str] = []
                seen = set()
                for idx, image_url in enumerate(raw_urls):
                    normalized = str(image_url or "").strip()
                    if not normalized or normalized in seen:
                        continue
                    seen.add(normalized)

                    final_url = normalized
                    if config.IMAGE_SAVE_ENABLED and self.storage_service and character_id:
                        local_path = self.storage_service.save_image(
                            normalized, character_id, user_id, image_type,
                            image_index=len(image_urls) + 1,
                        )
                        if local_path:
                            final_url = get_static_url(local_path, 'characters')
                    image_urls.append(final_url)
                    if len(image_urls) >= target_count:
                        break

                if image_urls:
                    logger.info(f"预览图生成完成: 成功生成 {len(image_urls)}/{group_count} 张图片")
                    return image_urls
                logger.warning("预览图生成失败: 未能生成任何图片")
                return None
            else:
                # 单张图片生成（原有逻辑）
                payload = {
                    "model": config.VOLCENGINE_IMAGE_MODEL,
                    "prompt": prompt,
                    "size": character_image_size,
                    "response_format": "url",
                    "watermark": False,
                }
                
                # 发送请求
                response = requests.post(
                    self.volcengine_api_url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                
                # 检查HTTP状态码
                if response.status_code != 200:
                    logger.warning(f"火山引擎API请求失败: HTTP {response.status_code}")
                    try:
                        resp_preview = response.text[:800]
                    except Exception:
                        resp_preview = "<unreadable response body>"
                    logger.warning(
                        "火山引擎图片生成HTTP失败: model=%s size=%s status=%s body=%s",
                        payload.get("model"),
                        payload.get("size"),
                        response.status_code,
                        resp_preview,
                    )
                    return None
                
                # 解析响应
                try:
                    resp_data = response.json()
                except Exception:
                    logger.warning(
                        "火山引擎图片生成响应不是JSON: model=%s size=%s status=%s body=%s",
                        payload.get("model"),
                        payload.get("size"),
                        response.status_code,
                        response.text[:800] if hasattr(response, "text") else "<no body>",
                    )
                    return None
                
                # 检查是否有错误
                if 'error' in resp_data:
                    error_info = resp_data['error']
                    error_msg = error_info.get('message', '未知错误')
                    error_code = error_info.get('code') or error_info.get('type') or None
                    logger.warning(f"火山引擎图片生成失败: {error_msg}")
                    logger.warning(
                        "火山引擎图片生成返回error: model=%s size=%s code=%s message=%s",
                        payload.get("model"),
                        payload.get("size"),
                        error_code,
                        error_msg,
                    )
                    return None
                
                # 提取图片URL
                if 'data' in resp_data and len(resp_data['data']) > 0:
                    image_data = resp_data['data'][0]
                    image_url = image_data.get('url')
                    if image_url:
                        logger.info(f"图片生成成功: {image_url}")
                        
                        # 保存图片到本地（如果启用且提供了存储服务）
                        final_url = image_url  # 默认使用临时URL
                        if config.IMAGE_SAVE_ENABLED and self.storage_service and character_id:
                            local_path = self.storage_service.save_image(
                                image_url, character_id, user_id, image_type
                            )
                            if local_path:
                                logger.info(f"图片已保存到本地: {local_path}")
                                # 构建静态文件URL（使用本地保存的文件）
                                final_url = get_static_url(local_path, 'characters')
                                logger.debug(f"使用本地静态文件URL: {final_url}")
                        
                        return [final_url]
                    else:
                        logger.warning(f"响应中未找到图片URL: {resp_data}")
                        return None
                else:
                    logger.warning(f"响应中未找到data字段或data为空: {resp_data}")
                    return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"火山引擎API请求异常: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"火山引擎图片生成异常: {e}", exc_info=True)
            return None
    
    def _generate_with_dashscope(self, prompt: str, character_id: Optional[int] = None,
                                 user_id: Optional[str] = None, image_type: str = 'portrait') -> Optional[str]:
        """使用通义万相生成图片
        
        Args:
            prompt: 图片生成prompt
            character_id: 角色ID（可选）
            user_id: 玩家ID（可选）
            image_type: 图片类型
            
        Returns:
            图片URL，如果失败返回None
        """
        try:
            logger.info(f"正在生成角色图片 (角色ID: {character_id})")
            logger.debug(f"Prompt: {prompt[:100]}...")
            
            response = ImageSynthesis.call(
                model='wanx-v1',  # 通义万相模型
                prompt=prompt,
                n=1,  # 生成1张图片
                size='1024*1024'  # 图片尺寸
            )
            
            if response.status_code == 200:
                image_url = response.output.results[0].url
                logger.info(f"图片生成成功: {image_url}")
                
                # 保存图片到本地（如果启用且提供了存储服务）
                final_url = image_url  # 默认使用临时URL
                if config.IMAGE_SAVE_ENABLED and self.storage_service and character_id:
                    local_path = self.storage_service.save_image(image_url, character_id, user_id, image_type)
                    if local_path:
                        logger.info(f"图片已保存到本地: {local_path}")
                        # 构建静态文件URL（使用本地保存的文件）
                        final_url = get_static_url(local_path, 'characters')
                        logger.debug(f"使用本地静态文件URL: {final_url}")
                
                return final_url
            else:
                logger.warning(f"通义万相图片生成失败: {response.message}")
                return None
        except Exception as e:
            logger.error(f"通义万相图片生成异常: {e}", exc_info=True)
            return None
    
    def _generate_scene_with_volcengine(self, prompt: str, scene_id: str, scene_name: str,
                                       user_id: Optional[str] = None) -> Optional[str]:
        """使用火山引擎生成场景图片
        
        Args:
            prompt: 场景图片生成prompt
            scene_id: 场景ID（用于文件命名）
            scene_name: 场景名称（用于文件命名）
            user_id: 玩家ID（可选）
            
        Returns:
            图片URL，如果失败返回None
        """
        try:
            logger.info(f"正在使用火山引擎Seedream生成场景图片 (场景ID: {scene_id})")
            logger.debug(f"Prompt: {prompt[:100]}...")
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {config.VOLCENGINE_ARK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # 场景图片使用16:9比例（2560x1440，满足最小像素要求 3,686,400）
            scene_image_size = "2560x1440"  # 16:9 比例，2K分辨率
            
            payload = {
                "model": config.VOLCENGINE_IMAGE_MODEL,
                "prompt": prompt,
                "size": scene_image_size,  # 场景图片固定为16:9，2K分辨率
                "response_format": "url",
                "watermark": False,  # 场景图不需要水印
            }
            
            # 发送请求
            response = requests.post(
                self.volcengine_api_url,
                headers=headers,
                json=payload,
                timeout=120  # 生图可能需要较长时间
            )
            
            # 检查HTTP状态码
            if response.status_code != 200:
                logger.warning(f"火山引擎API请求失败: HTTP {response.status_code}")
                logger.debug(f"响应内容: {response.text[:200]}")
                return None
            
            # 解析响应
            resp_data = response.json()
            
            # 检查是否有错误
            if 'error' in resp_data:
                error_info = resp_data['error']
                error_msg = error_info.get('message', '未知错误')
                logger.warning(f"火山引擎场景图片生成失败: {error_msg}")
                return None
            
            # 提取图片URL
            if 'data' in resp_data and len(resp_data['data']) > 0:
                # 取第一张图片的URL
                image_data = resp_data['data'][0]
                image_url = image_data.get('url')
                
                if image_url:
                    logger.info(f"场景图片生成成功: {image_url}")
                    final_url = image_url
                    # 保存图片到本地（如果启用且提供了存储服务）
                    if config.IMAGE_SAVE_ENABLED and self.storage_service:
                        local_path = self.storage_service.save_image(
                            image_url, None, user_id, 'scene', 
                            scene_id, scene_name
                        )
                        if local_path:
                            logger.info(f"场景图片已保存到本地: {local_path}")
                            final_url = get_static_url(
                                local_path,
                                self._resolve_scene_static_type(local_path),
                            )

                    return final_url
                else:
                    logger.warning(f"响应中未找到图片URL: {resp_data}")
                    return None
            else:
                logger.warning(f"响应中未找到data字段或data为空: {resp_data}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"火山引擎API请求异常: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"火山引擎场景图片生成异常: {e}", exc_info=True)
            return None
    
    def _generate_scene_with_dashscope(self, prompt: str, scene_id: str, scene_name: str,
                                      user_id: Optional[str] = None) -> Optional[str]:
        """使用通义万相生成场景图片
        
        Args:
            prompt: 场景图片生成prompt
            scene_id: 场景ID（用于文件命名）
            scene_name: 场景名称（用于文件命名）
            user_id: 玩家ID（可选）
            
        Returns:
            图片URL，如果失败返回None
        """
        try:
            logger.info(f"正在生成场景图片 (场景ID: {scene_id})")
            logger.debug(f"Prompt: {prompt[:100]}...")
            
            # 场景图片使用16:9比例（1920x1080）
            scene_image_size = '1920*1080'  # 16:9 比例
            
            response = ImageSynthesis.call(
                model='wanx-v1',  # 通义万相模型
                prompt=prompt,
                n=1,  # 生成1张图片
                size=scene_image_size  # 场景图片固定为16:9
            )
            
            if response.status_code == 200:
                image_url = response.output.results[0].url
                logger.info(f"场景图片生成成功: {image_url}")
                final_url = image_url
                # 保存图片到本地（如果启用且提供了存储服务）
                if config.IMAGE_SAVE_ENABLED and self.storage_service:
                    local_path = self.storage_service.save_image(
                        image_url, None, user_id, 'scene',
                        scene_id, scene_name
                    )
                    if local_path:
                        logger.info(f"场景图片已保存到本地: {local_path}")
                        final_url = get_static_url(
                            local_path,
                            self._resolve_scene_static_type(local_path),
                        )

                return final_url
            else:
                logger.warning(f"场景图片生成失败: {response.message}")
                return None
        except Exception as e:
            logger.error(f"通义万相场景图片生成异常: {e}", exc_info=True)
            return None

    @staticmethod
    def _resolve_scene_static_type(local_path: str) -> str:
        normalized_path = str(local_path or "").replace("\\", "/").lower()
        if "/smallscenes/" in normalized_path:
            return "smallscenes"
        return "scenes"
