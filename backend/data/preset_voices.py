"""预设音色库配置（火山引擎 Doubao TTS - 双向流式WebSocket API）"""

# 火山引擎 TTS 支持的音色列表
# 参考：https://www.volcengine.com/docs/82379/1263482

PRESET_VOICES = {
    'female': [
        {
            'id': 'female_001',
            'name': '通用女声',
            'description': '标准女声，适合通用场景',
            'provider': 'volcengine',
            'voice_id': 'BV001_streaming',  # 火山引擎标准女声
            'preview_text': '你好呀，很高兴见到你！',
            'gender': 'female',
            'style': '标准',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'female_002',
            'name': '温柔女声',
            'description': '温柔甜美女声，适合故事叙述、温馨对话',
            'provider': 'volcengine',
            'voice_id': 'BV002_streaming',  # 火山引擎温柔女声
            'preview_text': '今天天气真不错呢！',
            'gender': 'female',
            'style': '温柔甜美',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'female_003',
            'name': '活泼女声',
            'description': '活泼开朗女声，适合轻松愉快的场景',
            'provider': 'volcengine',
            'voice_id': 'BV003_streaming',  # 火山引擎活泼女声
            'preview_text': '你好，欢迎使用语音合成服务。',
            'gender': 'female',
            'style': '活泼开朗',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'female_004',
            'name': '情感女声',
            'description': '情感丰富女声，适合情感表达',
            'provider': 'volcengine',
            'voice_id': 'BV004_streaming',  # 火山引擎情感女声
            'preview_text': '这个故事真的很感人呢。',
            'gender': 'female',
            'style': '情感丰富',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True,
            'emotions': ['happy', 'sad', 'angry', 'surprised', 'neutral']
        },
        {
            'id': 'female_005',
            'name': '优雅女声',
            'description': '优雅女声，适合正式场合',
            'provider': 'volcengine',
            'voice_id': 'BV005_streaming',  # 火山引擎优雅女声
            'preview_text': '您好，很高兴为您服务。',
            'gender': 'female',
            'style': '优雅',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'female_006',
            'name': '双快思思（月亮版）',
            'description': '温柔甜美女声，适合故事叙述、温馨对话',
            'provider': 'volcengine',
            'voice_id': 'zh_female_shuangkuaisisi_moon_bigtts',
            'preview_text': '月光下的故事总是格外动人。',
            'gender': 'female',
            'style': '温柔甜美',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'female_007',
            'name': '双快思思（太阳版）',
            'description': '活泼开朗女声，适合轻松愉快的场景',
            'provider': 'volcengine',
            'voice_id': 'zh_female_shuangkuaisisi_sun_bigtts',
            'preview_text': '阳光明媚的日子里，一切都充满希望！',
            'gender': 'female',
            'style': '活泼开朗',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'female_008',
            'name': '艾佳（标准版）',
            'description': '清甜女声，适合日常对话',
            'provider': 'volcengine',
            'voice_id': 'zh_female_aijia_bigtts',
            'preview_text': '今天的天气真好呢，我们一起出去走走吧！',
            'gender': 'female',
            'style': '清甜自然',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'female_009',
            'name': '艾佳（情感版）',
            'description': '情感丰富女声，适合情感表达和故事叙述',
            'provider': 'volcengine',
            'voice_id': 'zh_female_aijia_emotion_bigtts',
            'preview_text': '这个故事让我想起了很多美好的回忆。',
            'gender': 'female',
            'style': '情感丰富',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': True,
            'supports_mix': True,
            'emotions': ['gentle', 'excited', 'melancholy', 'cheerful', 'neutral']
        },
        {
            'id': 'female_010',
            'name': '艾雅（清新版）',
            'description': '清新女声，适合轻松愉快的对话',
            'provider': 'volcengine',
            'voice_id': 'zh_female_aiya_bigtts',
            'preview_text': '哇，这个想法真的很棒呢！',
            'gender': 'female',
            'style': '清新活泼',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'female_011',
            'name': '知性女声',
            'description': '知性优雅女声，适合专业场景',
            'provider': 'volcengine',
            'voice_id': 'BV010_streaming',
            'preview_text': '让我们来深入分析一下这个问题。',
            'gender': 'female',
            'style': '知性优雅',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'female_012',
            'name': '甜美女声',
            'description': '甜美可爱女声，适合温馨场景',
            'provider': 'volcengine',
            'voice_id': 'BV011_streaming',
            'preview_text': '谢谢你陪伴我，我感到很开心！',
            'gender': 'female',
            'style': '甜美可爱',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
    ],
    'male': [
        {
            'id': 'male_001',
            'name': '标准男声',
            'description': '标准男声，适合播音、解说',
            'provider': 'volcengine',
            'voice_id': 'BV006_streaming',  # 火山引擎标准男声
            'preview_text': '大家好，欢迎收听今天的节目。',
            'gender': 'male',
            'style': '标准播音',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'male_002',
            'name': '情感男声',
            'description': '情感丰富男声，适合故事叙述',
            'provider': 'volcengine',
            'voice_id': 'BV007_streaming',  # 火山引擎情感男声
            'preview_text': '这是一个关于勇气的故事。',
            'gender': 'male',
            'style': '情感丰富',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True,
            'emotions': ['confident', 'gentle', 'serious', 'cheerful', 'neutral']
        },
        {
            'id': 'male_003',
            'name': '成熟男声',
            'description': '成熟男声，适合商务场景',
            'provider': 'volcengine',
            'voice_id': 'BV008_streaming',  # 火山引擎成熟男声
            'preview_text': '让我们来分析一下这个问题。',
            'gender': 'male',
            'style': '成熟稳重',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'male_004',
            'name': '年轻男声',
            'description': '年轻男声，适合轻松对话',
            'provider': 'volcengine',
            'voice_id': 'BV009_streaming',  # 火山引擎年轻男声
            'preview_text': '嘿，今天过得怎么样？',
            'gender': 'male',
            'style': '年轻活力',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'male_005',
            'name': '艾达（标准版）',
            'description': '标准男声，适合播音、解说',
            'provider': 'volcengine',
            'voice_id': 'zh_male_aida_bigtts',
            'preview_text': '欢迎来到知识的海洋。',
            'gender': 'male',
            'style': '标准播音',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'male_006',
            'name': '艾达（情感版）',
            'description': '情感丰富男声，适合故事叙述',
            'provider': 'volcengine',
            'voice_id': 'zh_male_aida_emotion_bigtts',
            'preview_text': '每个故事都有它独特的魅力。',
            'gender': 'male',
            'style': '情感丰富',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': True,
            'supports_mix': True,
            'emotions': ['passionate', 'calm', 'dramatic', 'warm', 'neutral']
        },
        {
            'id': 'male_007',
            'name': '艾伦（阳光版）',
            'description': '阳光男声，适合积极向上的场景',
            'provider': 'volcengine',
            'voice_id': 'zh_male_ailun_bigtts',
            'preview_text': '新的一天开始了，让我们充满活力地迎接挑战！',
            'gender': 'male',
            'style': '阳光活力',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'male_008',
            'name': '艾昆（沉稳版）',
            'description': '沉稳男声，适合正式场合',
            'provider': 'volcengine',
            'voice_id': 'zh_male_aikun_bigtts',
            'preview_text': '经过深思熟虑，我认为这个方案是可行的。',
            'gender': 'male',
            'style': '沉稳可靠',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': True,
            'supports_mix': True
        },
        {
            'id': 'male_009',
            'name': '磁性男声',
            'description': '磁性男声，适合深度对话',
            'provider': 'volcengine',
            'voice_id': 'BV012_streaming',
            'preview_text': '让我们一起探索这个有趣的话题。',
            'gender': 'male',
            'style': '磁性深沉',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
    ],
    'neutral': [
        {
            'id': 'neutral_001',
            'name': '默认音色',
            'description': '使用模型默认音色',
            'provider': 'volcengine',
            'voice_id': 'BV001_streaming',  # 默认使用标准女声
            'preview_text': '你好，我是你的伙伴。',
            'gender': 'neutral',
            'style': '默认',
            'model_version': 'seed-tts-2.0',
            'supports_emotion': True,
            'supports_mix': True
        },
    ],
    'custom': [
        {
            'id': 'custom_mix_001',
            'name': '混音示例（女声主导）',
            'description': '多音色混音示例，以女声为主',
            'provider': 'volcengine',
            'voice_id': 'custom_mix_bigtts',
            'preview_text': '这是一个混音音色的示例。',
            'gender': 'female',
            'style': '混音',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': False,
            'supports_mix': False,
            'is_mix': True,
            'mix_config': [
                {'source_speaker': 'BV001_streaming', 'mix_factor': 0.6},
                {'source_speaker': 'BV002_streaming', 'mix_factor': 0.4}
            ]
        },
        {
            'id': 'custom_mix_002',
            'name': '混音示例（男女平衡）',
            'description': '男女音色平衡混音',
            'provider': 'volcengine',
            'voice_id': 'custom_mix_bigtts',
            'preview_text': '平衡的声音带来和谐的感受。',
            'gender': 'neutral',
            'style': '混音',
            'model_version': 'seed-tts-1.0',
            'supports_emotion': False,
            'supports_mix': False,
            'is_mix': True,
            'mix_config': [
                {'source_speaker': 'BV001_streaming', 'mix_factor': 0.5},
                {'source_speaker': 'BV006_streaming', 'mix_factor': 0.5}
            ]
        }
    ]
}

# 火山引擎 TTS 支持的完整音色列表
VOLCENGINE_VOICES = {
    'seed_tts_2_0': [
        # 豆包语音合成模型2.0音色
        'BV001_streaming', 'BV002_streaming', 'BV003_streaming', 
        'BV004_streaming', 'BV005_streaming', 'BV006_streaming',
        'BV007_streaming', 'BV008_streaming', 'BV009_streaming',
        'BV010_streaming', 'BV011_streaming', 'BV012_streaming',
    ],
    'seed_tts_1_0': [
        # 豆包语音合成模型1.0音色
        'zh_female_shuangkuaisisi_moon_bigtts',
        'zh_female_shuangkuaisisi_sun_bigtts',
        'zh_male_aida_bigtts',
        'zh_male_aida_emotion_bigtts',
        'zh_female_aijia_bigtts',
        'zh_female_aijia_emotion_bigtts',
        'zh_female_aiya_bigtts',
        'zh_male_ailun_bigtts',
        'zh_male_aikun_bigtts',
    ],
    'icl_voices': [
        # 声音复刻音色（以icl_或saturn_开头）
        # 这些需要通过API查询获取
    ],
    'all': []  # 将在运行时填充
}

# 填充所有音色列表
VOLCENGINE_VOICES['all'] = (
    VOLCENGINE_VOICES['seed_tts_2_0'] + 
    VOLCENGINE_VOICES['seed_tts_1_0'] + 
    VOLCENGINE_VOICES['icl_voices']
)

# 支持的情感列表
SUPPORTED_EMOTIONS = {
    'happy': '开心',
    'sad': '悲伤', 
    'angry': '愤怒',
    'surprised': '惊讶',
    'neutral': '中性',
    'confident': '自信',
    'gentle': '温柔',
    'serious': '严肃',
    'cheerful': '愉快',
    'passionate': '热情',
    'calm': '平静',
    'dramatic': '戏剧化',
    'warm': '温暖'
}

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh-cn': '中文（中国）',
    'en': '英语',
    'ja': '日语',
    'es-mx': '西班牙语（墨西哥）',
    'id': '印尼语',
    'pt-br': '葡萄牙语（巴西）',
    'de': '德语',
    'fr': '法语'
}

def get_preset_voices_by_gender(gender: str) -> list:
    """根据性别获取预设音色列表"""
    return PRESET_VOICES.get(gender.lower(), PRESET_VOICES['neutral'])

def get_preset_voice(voice_id: str) -> dict:
    """根据ID获取预设音色"""
    for category in PRESET_VOICES.values():
        for voice in category:
            if voice['id'] == voice_id:
                return voice
    return None

def get_all_preset_voices() -> dict:
    """获取所有预设音色"""
    return PRESET_VOICES

def get_voices_by_model(model_version: str) -> list:
    """根据模型版本获取音色列表"""
    voices = []
    for category in PRESET_VOICES.values():
        for voice in category:
            if voice.get('model_version') == model_version:
                voices.append(voice)
    return voices

def get_emotion_voices() -> list:
    """获取支持情感的音色列表"""
    voices = []
    for category in PRESET_VOICES.values():
        for voice in category:
            if voice.get('supports_emotion', False):
                voices.append(voice)
    return voices

def get_mix_voices() -> list:
    """获取支持混音的音色列表"""
    voices = []
    for category in PRESET_VOICES.values():
        for voice in category:
            if voice.get('supports_mix', False):
                voices.append(voice)
    return voices

def create_mix_config(speakers: list) -> dict:
    """创建混音配置
    
    Args:
        speakers: 音色配置列表，格式：[{'voice_id': 'BV001_streaming', 'factor': 0.6}, ...]
    
    Returns:
        混音配置字典
    """
    if not speakers or len(speakers) > 3:
        raise ValueError("混音音色数量必须在1-3个之间")
    
    total_factor = sum(s.get('factor', 0) for s in speakers)
    if abs(total_factor - 1.0) > 0.01:
        raise ValueError("混音因子总和必须等于1.0")
    
    return {
        'speakers': [
            {
                'source_speaker': s['voice_id'],
                'mix_factor': s['factor']
            }
            for s in speakers
        ]
    }

def get_preset_voices_by_gender(gender: str) -> list:
    """根据性别获取预设音色列表"""
    return PRESET_VOICES.get(gender.lower(), PRESET_VOICES['neutral'])

def get_preset_voice(voice_id: str) -> dict:
    """根据ID获取预设音色"""
    for category in PRESET_VOICES.values():
        for voice in category:
            if voice['id'] == voice_id:
                return voice
    return None

def get_all_preset_voices() -> dict:
    """获取所有预设音色"""
    return PRESET_VOICES
