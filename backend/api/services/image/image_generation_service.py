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
        
        return prompt
    
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
            
            # 如果生成组图，循环调用API生成多张不同变体的图片
            if generate_group and group_count > 1:
                image_urls = []
                
                # 定义每张图片的变体描述（让3张图片有差异）
                variant_descriptions = [
                    "正面全身像，微笑表情，自然站立姿势",
                    "正面全身像，温和表情，优雅姿态",
                    "正面半身像，自信表情，手部动作"
                ]
                
                # 如果组图数量超过预定义的变体数量，循环使用
                for i in range(group_count):
                    variant_idx = i % len(variant_descriptions)
                    variant_desc = variant_descriptions[variant_idx]
                    
                    # 为每张图片构建独特的prompt
                    variant_prompt = f"{prompt}，{variant_desc}"
                    
                    logger.debug(f"正在生成第 {i + 1}/{group_count} 张图片...")
                    logger.debug(f"变体Prompt: {variant_prompt[:120]}...")
                    
                    # 构建请求体
                    payload = {
                        "model": config.VOLCENGINE_IMAGE_MODEL,
                        "prompt": variant_prompt,
                        "size": character_image_size,
                        "response_format": "url",
                        "watermark": False,  # 不带水印
                        "stream": False  # 非流式输出
                    }
                    
                    # 发送请求
                    response = requests.post(
                        self.volcengine_api_url,
                        headers=headers,
                        json=payload,
                        timeout=120  # 单张图片生成超时时间
                    )
                    
                    # 检查HTTP状态码
                    if response.status_code != 200:
                        logger.warning(f"第 {i + 1} 张图片生成失败: HTTP {response.status_code}")
                        logger.debug(f"响应内容: {response.text[:200]}")
                        continue  # 继续生成下一张
                    
                    # 解析响应
                    resp_data = response.json()
                    
                    # 检查是否有错误
                    if 'error' in resp_data:
                        error_info = resp_data['error']
                        error_msg = error_info.get('message', '未知错误')
                        logger.warning(f"第 {i + 1} 张图片生成失败: {error_msg}")
                        continue  # 继续生成下一张
                    
                    # 提取图片URL
                    if 'data' in resp_data and len(resp_data['data']) > 0:
                        image_data = resp_data['data'][0]  # 每次调用只生成一张图片
                        image_url = image_data.get('url')
                        if image_url:
                            logger.info(f"第 {i + 1} 张图片生成成功: {image_url}")
                            
                            # 保存图片到本地（如果启用且提供了存储服务）
                            final_url = image_url  # 默认使用临时URL
                            
                            if config.IMAGE_SAVE_ENABLED and self.storage_service and character_id:
                                logger.debug(f"开始保存第 {i + 1} 张图片到本地...")
                                local_path = self.storage_service.save_image(
                                    image_url, character_id, user_id, image_type,
                                    image_index=i + 1  # 图片索引（1, 2, 3）
                                )
                                if local_path:
                                    logger.info(f"第 {i + 1} 张图片已保存到本地: {local_path}")
                                    # 构建静态文件URL（使用本地保存的文件）
                                    final_url = get_static_url(local_path, 'characters')
                                    logger.debug(f"使用本地静态文件URL: {final_url}")
                                else:
                                    logger.warning(f"第 {i + 1} 张图片保存失败: 返回路径为None，使用临时URL")
                            elif not character_id:
                                logger.debug(f"第 {i + 1} 张图片未保存: character_id为None，使用临时URL")
                            
                            image_urls.append(final_url)
                        else:
                            logger.warning(f"第 {i + 1} 张图片响应中未找到URL")
                    else:
                        logger.warning(f"第 {i + 1} 张图片响应中未找到data字段")
                
                # 检查是否成功生成了至少一张图片
                if image_urls:
                    logger.info(f"组图生成完成: 成功生成 {len(image_urls)}/{group_count} 张图片")
                    return image_urls
                else:
                    logger.warning("组图生成失败: 未能生成任何图片")
                    return None
            else:
                # 单张图片生成（原有逻辑）
                payload = {
                    "model": config.VOLCENGINE_IMAGE_MODEL,
                    "prompt": prompt,
                    "size": character_image_size,
                    "response_format": "url",
                    "watermark": False,
                    "stream": False
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
                    logger.debug(f"响应内容: {response.text[:200]}")
                    return None
                
                # 解析响应
                resp_data = response.json()
                
                # 检查是否有错误
                if 'error' in resp_data:
                    error_info = resp_data['error']
                    error_msg = error_info.get('message', '未知错误')
                    logger.warning(f"火山引擎图片生成失败: {error_msg}")
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
                "stream": False  # 非流式输出
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
                    
                    # 保存图片到本地（如果启用且提供了存储服务）
                    if config.IMAGE_SAVE_ENABLED and self.storage_service:
                        local_path = self.storage_service.save_image(
                            image_url, None, user_id, 'scene', 
                            scene_id, scene_name
                        )
                        if local_path:
                            logger.info(f"场景图片已保存到本地: {local_path}")
                    
                    return image_url
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
                
                # 保存图片到本地（如果启用且提供了存储服务）
                if config.IMAGE_SAVE_ENABLED and self.storage_service:
                    local_path = self.storage_service.save_image(
                        image_url, None, user_id, 'scene',
                        scene_id, scene_name
                    )
                    if local_path:
                        logger.info(f"场景图片已保存到本地: {local_path}")
                
                return image_url
            else:
                logger.warning(f"场景图片生成失败: {response.message}")
                return None
        except Exception as e:
            logger.error(f"通义万相场景图片生成异常: {e}", exc_info=True)
            return None
