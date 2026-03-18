"""场景数据"""

# 大场景定义：大场景只用于生成关键词，不直接用于游戏
# 大场景包含多个小场景，小场景才是实际用于游戏的场景
MAJOR_SCENES = {
    'school': {
        'name': '学校',
        'description': '一个充满青春气息的校园场景',
        'keyword': '学校 校园 学生 青春',
        # 该大场景下的小场景列表
        'sub_scenes': [
        'library',      # 图书馆
        'classroom',    # 教室
        'cafeteria',    # 食堂
        'playground',   # 操场
        'dormitory',    # 宿舍
        'campus_path',  # 校园小径
        'school_gate',  # 校门口
        'rooftop',      # 天台
        'gym',          # 体育馆
            'cafe_nearby',  # 学校附近的咖啡厅
            'bookstore',    # 书店
            'lab',          # 实验室
            'art_room',     # 美术室
            'music_room',   # 音乐室
            'study_room',   # 自习室
            'basketball_court',  # 篮球场
            'swimming_pool',     # 游泳池
            'student_union',     # 学生会办公室
            'canteen_terrace',   # 食堂露台
            'school_garden'      # 校园花园
        ]
    },
    'company': {
        'name': '公司',
        'description': '职场工作环境，充满专业和协作氛围',
        'keyword': '公司 职场 工作 办公 同事 职业 业务 工作环境',
        'sub_scenes': [
            'office_desk',      # 办公桌
            'meeting_room',      # 会议室
            'break_room',        # 休息室
            'reception',         # 前台
            'elevator',          # 电梯
            'parking_lot',       # 停车场
            'company_cafeteria', # 公司食堂
            'lounge',            # 休息区
            'copy_room',         # 复印室
            'coffee_corner',     # 咖啡角
            'training_room',     # 培训室
            'office_balcony'     # 办公室阳台
        ]
    },
    'dailylife': {
        'name': '日常生活',
        'description': '日常生活中的各种场景，贴近生活，自然真实',
        'keyword': '日常生活 日常 生活 生活场景 日常活动 生活化',
        'sub_scenes': [
            'convenience_store', # 便利店
            'residential_area',  # 小区
            'community_park',    # 社区公园
            'delivery_station',  # 快递站
            'residential_gate',  # 小区门口
            'community_center',  # 社区活动中心
            'pet_shop',          # 宠物店
            'supermarket',       # 超市
            'pharmacy',          # 药店
            'laundry',           # 洗衣店
            'bakery',            # 面包店
            'fruit_stand'        # 水果摊
        ]
    },
    'leisure': {
        'name': '休闲娱乐',
        'description': '轻松愉快的休闲娱乐场所，适合放松和娱乐',
        'keyword': '休闲 娱乐 放松 轻松 愉快 休闲时光 娱乐活动',
        'sub_scenes': [
            'shopping_mall',     # 购物中心
            'cinema',            # 电影院
            'arcade',            # 游戏厅
            'ktv',               # KTV
            'amusement_park',    # 游乐园
            'aquarium',          # 水族馆
            'zoo',               # 动物园
            'theme_park',        # 主题公园
            'escape_room',       # 密室逃脱
            'board_game_cafe',   # 桌游吧
            'bowling_alley',     # 保龄球馆
            'billiards_hall'     # 台球厅
        ]
    },
    'nature': {
        'name': '自然户外',
        'description': '自然清新的户外环境，宁静而美好',
        'keyword': '自然 户外 清新 宁静 自然风光 户外活动 大自然',
        'sub_scenes': [
            'city_park',         # 城市公园
            'lakeside',          # 湖边
            'hilltop_view',      # 山顶观景台
            'forest_path',       # 森林小径
            'flower_garden',     # 花海
            'lawn',              # 草坪
            'pavilion',          # 凉亭
            'trail',             # 步道
            'riverside',         # 河边
            'beach',             # 海滩
            'mountain_path',     # 山间小径
            'sunset_point'       # 观日落点
        ]
    },
    'cultural': {
        'name': '文化学习',
        'description': '充满文化氛围的学习和艺术场所',
        'keyword': '文化 学习 知识 艺术 文化氛围 学习交流 文化场所',
        'sub_scenes': [
            'public_library',    # 公共图书馆
            'museum',            # 博物馆
            'art_gallery',       # 艺术馆
            'concert_hall',      # 音乐厅
            'exhibition_hall',   # 展览馆
            'cultural_center',  # 文化中心
            'independent_bookstore', # 独立书店
            'theater',           # 剧院
            'gallery',           # 画廊
            'reading_room',      # 阅览室
            'workshop',          # 工作坊
            'studio'             # 工作室
        ]
    }
}

# 小场景定义：小场景是实际用于游戏的场景
# 每个小场景属于一个大场景，用于场景切换时的逻辑判断
SUB_SCENES = {
    'library': {
        'name': '图书馆',
        'description': '安静的学习空间，书香四溢。整齐排列的书架间，偶尔传来翻书声和低语，阳光透过窗户洒在书桌上，营造出专注学习的氛围',
        'major_scene': 'school',
        'keywords': '图书馆 书籍 阅读 学习 安静 书架 自习 借书'
    },
    'classroom': {
        'name': '教室',
        'description': '日常上课的地方，充满学习氛围。黑板前摆放着讲台，整齐的桌椅排列成行，墙上贴着课程表和励志标语，是学生们获取知识的主要场所',
        'major_scene': 'school',
        'keywords': '教室 上课 学习 课堂 黑板 讲台 座位 听课'
    },
    'cafeteria': {
        'name': '食堂',
        'description': '学生们用餐的地方，热闹而温馨。午餐时间人声鼎沸，各种美食的香味弥漫在空气中，同学们围坐在一起边吃边聊，充满了生活气息',
        'major_scene': 'school',
        'keywords': '食堂 用餐 吃饭 食物 热闹 午餐 排队 餐桌'
    },
    'playground': {
        'name': '操场',
        'description': '宽阔的运动场地，充满活力。红色的塑胶跑道环绕着绿色的草坪，学生们在这里跑步、踢球、做运动，挥洒着青春的汗水',
        'major_scene': 'school',
        'keywords': '操场 运动 跑步 锻炼 活力 跑道 草坪 体育课'
    },
    'dormitory': {
        'name': '宿舍',
        'description': '学生们的休息空间，私密而舒适。小小的房间里摆放着床铺和书桌，是学生们放松、聊天、学习的地方，充满了生活的痕迹',
        'major_scene': 'school',
        'keywords': '宿舍 休息 私密 舒适 生活 床铺 室友 聊天'
    },
    'campus_path': {
        'name': '校园小径',
        'description': '连接校园各处的林荫小道。两旁种满了绿树，阳光透过树叶洒下斑驳的光影，是学生们上下课必经的安静小路，偶尔能听到鸟鸣声',
        'major_scene': 'school',
        'keywords': '校园小径 林荫小道 散步 安静 绿树 光影 小路'
    },
    'school_gate': {
        'name': '校门口',
        'description': '学校的出入口，人来人往。每天早晨和傍晚，这里都会聚集很多学生，有的匆忙赶路，有的悠闲聊天，是校园生活的起点和终点',
        'major_scene': 'school',
        'keywords': '校门口 出入口 人来人往 进出 上学 放学 等待'
    },
    'rooftop': {
        'name': '天台',
        'description': '学校建筑的顶层，视野开阔。站在这里可以俯瞰整个校园，远处的风景尽收眼底，是学生们放松心情、思考人生的好地方',
        'major_scene': 'school',
        'keywords': '天台 顶层 视野 开阔 高处 俯瞰 风景 思考'
    },
    'gym': {
        'name': '体育馆',
        'description': '室内运动场所，设施完善。宽敞的场地内摆放着各种运动器材，篮球架、羽毛球网、乒乓球台一应俱全，是学生们进行室内运动的好去处',
        'major_scene': 'school',
        'keywords': '体育馆 室内运动 设施 锻炼 器材 篮球 羽毛球'
    },
    'cafe_nearby': {
        'name': '学校附近的咖啡厅',
        'description': '温馨的咖啡厅，适合聊天和学习。柔和的灯光、舒适的座椅、浓郁的咖啡香，是学生们课后放松、讨论作业、约会见面的理想场所',
        'major_scene': 'school',
        'keywords': '咖啡厅 咖啡 聊天 学习 温馨 约会 放松 讨论'
    },
    'bookstore': {
        'name': '书店',
        'description': '琳琅满目的书籍，安静而优雅。书架上整齐地排列着各类书籍，从教科书到小说应有尽有，是爱书之人流连忘返的地方',
        'major_scene': 'school',
        'keywords': '书店 书籍 阅读 安静 优雅 书架 选书 买书'
    },
    'lab': {
        'name': '实验室',
        'description': '充满科学气息的实验空间。整齐的实验台、各种实验器材和仪器，空气中弥漫着淡淡的化学试剂味道，是学生们进行科学探索的地方',
        'major_scene': 'school',
        'keywords': '实验室 实验 科学 器材 仪器 化学 物理 探索'
    },
    'art_room': {
        'name': '美术室',
        'description': '充满艺术氛围的创作空间。墙上挂着学生们的作品，画架上摆放着未完成的画作，各种颜料和画笔散落在桌上，是艺术爱好者展现才华的地方',
        'major_scene': 'school',
        'keywords': '美术室 绘画 艺术 创作 画架 颜料 画笔 作品'
    },
    'music_room': {
        'name': '音乐室',
        'description': '充满旋律的音乐空间。钢琴、吉他等乐器整齐摆放，墙上贴着乐谱，是音乐爱好者练习和表演的场所，时常能听到优美的琴声',
        'major_scene': 'school',
        'keywords': '音乐室 音乐 乐器 钢琴 吉他 乐谱 练习 表演'
    },
    'study_room': {
        'name': '自习室',
        'description': '安静专注的学习空间。一排排书桌整齐排列，学生们埋头苦读，只能听到翻书声和笔尖划过纸张的声音，是备考和复习的理想场所',
        'major_scene': 'school',
        'keywords': '自习室 自习 学习 复习 备考 安静 专注 书桌'
    },
    'basketball_court': {
        'name': '篮球场',
        'description': '充满活力的运动场地。标准的篮球架、清晰的场地线，学生们在这里挥洒汗水，运球、投篮、配合，充满了青春的运动气息',
        'major_scene': 'school',
        'keywords': '篮球场 篮球 运动 投篮 运球 比赛 训练 活力'
    },
    'swimming_pool': {
        'name': '游泳池',
        'description': '清澈的泳池，波光粼粼。学生们在水中游泳、嬉戏，水花四溅，是夏日里最受欢迎的地方，充满了清凉和活力',
        'major_scene': 'school',
        'keywords': '游泳池 游泳 水 清凉 运动 训练 嬉戏 夏日'
    },
    'student_union': {
        'name': '学生会办公室',
        'description': '学生组织的活动中心。办公室里摆放着会议桌和文件柜，墙上贴着各种活动海报，是学生们讨论活动、处理事务的地方',
        'major_scene': 'school',
        'keywords': '学生会 办公室 活动 会议 讨论 组织 事务 海报'
    },
    'canteen_terrace': {
        'name': '食堂露台',
        'description': '食堂外的露天平台。摆放着几张桌椅，可以在这里享受阳光和微风，是学生们饭后休息、聊天、看风景的好地方',
        'major_scene': 'school',
        'keywords': '食堂露台 露台 户外 休息 聊天 阳光 微风 风景'
    },
    'school_garden': {
        'name': '校园花园',
        'description': '美丽的校园花园。各种花草树木错落有致，小径蜿蜒其中，是学生们散步、休息、思考的宁静场所，充满了自然的气息',
        'major_scene': 'school',
        'keywords': '校园花园 花园 花草 树木 散步 休息 自然 宁静'
    },
    # 公司场景
    'office_desk': {
        'name': '办公桌',
        'description': '整洁的办公区域，电脑、文件、文具整齐摆放。同事们各自忙碌着，键盘敲击声和电话铃声此起彼伏，充满了工作的氛围',
        'major_scene': 'company',
        'keywords': '办公桌 办公 工作 电脑 文件 办公区域 同事'
    },
    'meeting_room': {
        'name': '会议室',
        'description': '专业的会议室，投影仪、白板、会议桌一应俱全。这里是讨论工作、汇报项目、团队协作的地方，充满了商务氛围',
        'major_scene': 'company',
        'keywords': '会议室 会议 讨论 汇报 投影 白板 商务'
    },
    'break_room': {
        'name': '休息室',
        'description': '舒适的休息空间，有沙发、茶几、饮水机。午休时间同事们会在这里休息、聊天、喝咖啡，是工作间隙放松的地方',
        'major_scene': 'company',
        'keywords': '休息室 休息 放松 午休 聊天 咖啡 沙发'
    },
    'reception': {
        'name': '前台',
        'description': '公司前台接待区，整洁明亮。前台工作人员热情地接待来访者，这里是公司的门面，也是员工和访客的必经之地',
        'major_scene': 'company',
        'keywords': '前台 接待 来访 门面 工作人员 访客'
    },
    'elevator': {
        'name': '电梯',
        'description': '公司大楼的电梯间，每天上下班高峰期人来人往。在狭小的空间里，同事们有了短暂的交流机会，是职场偶遇的常见场所',
        'major_scene': 'company',
        'keywords': '电梯 上下班 偶遇 交流 狭小空间 同事'
    },
    'parking_lot': {
        'name': '停车场',
        'description': '公司地下的停车场，整齐停放着各种车辆。下班时间，同事们在这里取车，偶尔会在这里遇到，简单打个招呼',
        'major_scene': 'company',
        'keywords': '停车场 停车 取车 下班 车辆 偶遇'
    },
    'company_cafeteria': {
        'name': '公司食堂',
        'description': '公司内部的员工食堂，午餐时间人声鼎沸。同事们围坐在一起用餐，边吃边聊工作或生活，是职场社交的重要场所',
        'major_scene': 'company',
        'keywords': '公司食堂 午餐 用餐 同事 职场社交 聊天'
    },
    'lounge': {
        'name': '休息区',
        'description': '宽敞的休息区域，有舒适的沙发和茶几。工作累了可以在这里小憩，喝杯咖啡，和同事聊聊天，放松一下心情',
        'major_scene': 'company',
        'keywords': '休息区 小憩 咖啡 放松 沙发 聊天'
    },
    'copy_room': {
        'name': '复印室',
        'description': '设备齐全的复印室，有打印机、复印机、扫描仪。同事们经常来这里打印文件、复印资料，是工作中经常遇到的地方',
        'major_scene': 'company',
        'keywords': '复印室 打印 复印 扫描 文件 资料 设备'
    },
    'coffee_corner': {
        'name': '咖啡角',
        'description': '公司里的咖啡角，有咖啡机和各种饮品。工作间隙，同事们会来这里冲杯咖啡，提提神，顺便聊几句',
        'major_scene': 'company',
        'keywords': '咖啡角 咖啡 饮品 提神 工作间隙 聊天'
    },
    'training_room': {
        'name': '培训室',
        'description': '专业的培训教室，有投影设备和培训桌椅。新员工培训、技能提升课程都在这里进行，是学习和交流的地方',
        'major_scene': 'company',
        'keywords': '培训室 培训 学习 课程 新员工 技能提升'
    },
    'office_balcony': {
        'name': '办公室阳台',
        'description': '办公室外的阳台，视野开阔。工作累了可以来这里透透气，看看远处的风景，放松一下心情，偶尔会遇到同事',
        'major_scene': 'company',
        'keywords': '办公室阳台 阳台 透气 风景 放松 视野'
    },
    # 日常生活场景
    'convenience_store': {
        'name': '便利店',
        'description': '24小时营业的便利店，商品琳琅满目。晚上或清晨，这里总是有顾客进进出出，是日常生活中最常去的地方之一',
        'major_scene': 'dailylife',
        'keywords': '便利店 24小时 商品 购物 日常 生活'
    },
    'residential_area': {
        'name': '小区',
        'description': '安静的居民小区，绿树成荫。傍晚时分，居民们会在小区里散步、遛狗、聊天，充满了生活气息',
        'major_scene': 'dailylife',
        'keywords': '小区 居民 散步 遛狗 生活 安静'
    },
    'community_park': {
        'name': '社区公园',
        'description': '小区附近的社区公园，有健身器材和休闲设施。早晨和傍晚，附近的居民会来这里锻炼、散步、下棋，是社区生活的中心',
        'major_scene': 'dailylife',
        'keywords': '社区公园 公园 锻炼 散步 下棋 健身器材'
    },
    'delivery_station': {
        'name': '快递站',
        'description': '小区里的快递收发站，每天都有很多包裹。取快递时经常会遇到邻居，简单聊几句，是邻里交流的常见场所',
        'major_scene': 'dailylife',
        'keywords': '快递站 快递 包裹 取件 邻居 邻里交流'
    },
    'residential_gate': {
        'name': '小区门口',
        'description': '小区的出入口，保安亭、门禁系统一应俱全。每天进出都会经过这里，是日常生活中最熟悉的地方',
        'major_scene': 'dailylife',
        'keywords': '小区门口 出入口 门禁 保安 进出 熟悉'
    },
    'community_center': {
        'name': '社区活动中心',
        'description': '社区的活动中心，有各种活动室和设施。周末会有各种社区活动，居民们会来这里参加，是社区社交的场所',
        'major_scene': 'dailylife',
        'keywords': '社区活动中心 活动 社区 社交 周末 设施'
    },
    'pet_shop': {
        'name': '宠物店',
        'description': '温馨的宠物店，各种可爱的宠物和宠物用品。爱宠人士会经常来这里，给宠物买食物、玩具，或者只是看看可爱的小动物',
        'major_scene': 'dailylife',
        'keywords': '宠物店 宠物 可爱 宠物用品 爱宠 小动物'
    },
    'supermarket': {
        'name': '超市',
        'description': '大型超市，商品种类丰富。周末或下班后，人们会来这里采购生活用品，推着购物车在货架间穿梭，是日常购物的地方',
        'major_scene': 'dailylife',
        'keywords': '超市 购物 生活用品 货架 采购 商品'
    },
    'pharmacy': {
        'name': '药店',
        'description': '整洁的药店，各种药品和保健品整齐摆放。身体不适时会来这里买药，药师会耐心地询问症状，给出建议',
        'major_scene': 'dailylife',
        'keywords': '药店 药品 保健品 买药 药师 健康'
    },
    'laundry': {
        'name': '洗衣店',
        'description': '专业的洗衣店，有干洗和普通清洗服务。需要清洗特殊衣物时会来这里，等待时可以看看杂志，和老板聊聊天',
        'major_scene': 'dailylife',
        'keywords': '洗衣店 干洗 清洗 衣物 等待 聊天'
    },
    'bakery': {
        'name': '面包店',
        'description': '香气四溢的面包店，各种新鲜出炉的面包和糕点。早晨或下午，人们会来这里买早餐或下午茶，是日常生活中的小确幸',
        'major_scene': 'dailylife',
        'keywords': '面包店 面包 糕点 早餐 下午茶 香气'
    },
    'fruit_stand': {
        'name': '水果摊',
        'description': '路边的小水果摊，各种新鲜水果整齐摆放。下班路上会顺便买些水果，摊主热情地推荐当季水果，是日常生活中的小场景',
        'major_scene': 'dailylife',
        'keywords': '水果摊 水果 新鲜 当季 路边 小摊'
    },
    # 休闲娱乐场景
    'shopping_mall': {
        'name': '购物中心',
        'description': '大型购物中心，各种品牌店铺和餐厅。周末或节假日，人们会来这里购物、吃饭、看电影，是休闲娱乐的好去处',
        'major_scene': 'leisure',
        'keywords': '购物中心 购物 品牌 餐厅 周末 休闲'
    },
    'cinema': {
        'name': '电影院',
        'description': '现代化的电影院，舒适的座椅和震撼的音效。周末或晚上，人们会来这里看电影，在黑暗中享受电影带来的感动和刺激',
        'major_scene': 'leisure',
        'keywords': '电影院 电影 观影 周末 晚上 娱乐'
    },
    'arcade': {
        'name': '游戏厅',
        'description': '充满游戏机的游戏厅，各种电子游戏和抓娃娃机。年轻人会来这里放松娱乐，在游戏中寻找乐趣和刺激',
        'major_scene': 'leisure',
        'keywords': '游戏厅 游戏 电子游戏 抓娃娃 娱乐 放松'
    },
    'ktv': {
        'name': 'KTV',
        'description': '私密的KTV包间，音响设备和点歌系统一应俱全。朋友们会来这里唱歌、聊天、放松，是聚会娱乐的场所',
        'major_scene': 'leisure',
        'keywords': 'KTV 唱歌 包间 聚会 娱乐 放松'
    },
    'amusement_park': {
        'name': '游乐园',
        'description': '充满欢声笑语的游乐园，各种刺激的游乐设施。周末或节假日，人们会来这里体验过山车、旋转木马等，寻找童年的快乐',
        'major_scene': 'leisure',
        'keywords': '游乐园 游乐设施 过山车 旋转木马 快乐 刺激'
    },
    'aquarium': {
        'name': '水族馆',
        'description': '神秘的水族馆，各种海洋生物在巨大的水族箱中游弋。人们会来这里观赏海洋生物，感受海洋的奇妙和美丽',
        'major_scene': 'leisure',
        'keywords': '水族馆 海洋生物 水族箱 观赏 奇妙 美丽'
    },
    'zoo': {
        'name': '动物园',
        'description': '充满生机的动物园，各种动物在各自的区域生活。周末或节假日，人们会来这里观赏动物，了解自然，是亲子活动的好地方',
        'major_scene': 'leisure',
        'keywords': '动物园 动物 观赏 自然 亲子 周末'
    },
    'theme_park': {
        'name': '主题公园',
        'description': '以特定主题打造的公园，有独特的建筑和设施。人们会来这里体验主题文化，拍照留念，是休闲娱乐的好去处',
        'major_scene': 'leisure',
        'keywords': '主题公园 主题 文化 体验 拍照 休闲'
    },
    'escape_room': {
        'name': '密室逃脱',
        'description': '充满谜题和挑战的密室，需要团队合作解开谜题。朋友们会来这里挑战智力，体验紧张刺激的解谜过程',
        'major_scene': 'leisure',
        'keywords': '密室逃脱 谜题 挑战 团队合作 解谜 刺激'
    },
    'board_game_cafe': {
        'name': '桌游吧',
        'description': '温馨的桌游吧，各种桌游和舒适的座位。朋友们会来这里玩桌游、聊天、喝饮料，是轻松愉快的聚会场所',
        'major_scene': 'leisure',
        'keywords': '桌游吧 桌游 聚会 聊天 轻松 愉快'
    },
    'bowling_alley': {
        'name': '保龄球馆',
        'description': '专业的保龄球馆，标准的球道和设施。朋友们会来这里打保龄球，体验运动的乐趣，是休闲运动的好去处',
        'major_scene': 'leisure',
        'keywords': '保龄球馆 保龄球 运动 球道 休闲 乐趣'
    },
    'billiards_hall': {
        'name': '台球厅',
        'description': '专业的台球厅，整齐的台球桌和良好的灯光。朋友们会来这里打台球，切磋技艺，是休闲娱乐的场所',
        'major_scene': 'leisure',
        'keywords': '台球厅 台球 切磋 技艺 休闲 娱乐'
    },
    # 自然户外场景
    'city_park': {
        'name': '城市公园',
        'description': '城市中的大型公园，绿树成荫，鸟语花香。周末或傍晚，人们会来这里散步、跑步、野餐，享受自然的美好',
        'major_scene': 'nature',
        'keywords': '城市公园 公园 散步 跑步 野餐 自然'
    },
    'lakeside': {
        'name': '湖边',
        'description': '宁静的湖边，湖水清澈，微风拂面。人们会来这里散步、钓鱼、看风景，享受湖光山色的宁静和美好',
        'major_scene': 'nature',
        'keywords': '湖边 湖水 散步 钓鱼 风景 宁静'
    },
    'hilltop_view': {
        'name': '山顶观景台',
        'description': '山顶的观景台，视野开阔，可以俯瞰整个城市。人们会来这里看日出、日落，欣赏城市的美景，感受自然的壮丽',
        'major_scene': 'nature',
        'keywords': '山顶观景台 山顶 观景 日出 日落 壮丽'
    },
    'forest_path': {
        'name': '森林小径',
        'description': '幽静的森林小径，两旁是茂密的树木。人们会来这里徒步、呼吸新鲜空气，感受大自然的宁静和神秘',
        'major_scene': 'nature',
        'keywords': '森林小径 森林 徒步 新鲜空气 宁静 神秘'
    },
    'flower_garden': {
        'name': '花海',
        'description': '美丽的花海，各种鲜花盛开，色彩斑斓。人们会来这里赏花、拍照，感受花海的美丽和浪漫',
        'major_scene': 'nature',
        'keywords': '花海 鲜花 赏花 拍照 美丽 浪漫'
    },
    'lawn': {
        'name': '草坪',
        'description': '宽阔的绿色草坪，柔软舒适。人们会在这里野餐、晒太阳、放风筝，享受阳光和自然的惬意',
        'major_scene': 'nature',
        'keywords': '草坪 野餐 晒太阳 放风筝 阳光 惬意'
    },
    'pavilion': {
        'name': '凉亭',
        'description': '公园里的凉亭，有座椅和遮阳顶。人们会在这里休息、聊天、看风景，是公园里常见的休息场所',
        'major_scene': 'nature',
        'keywords': '凉亭 休息 聊天 看风景 遮阳 座椅'
    },
    'trail': {
        'name': '步道',
        'description': '蜿蜒的步道，两旁是自然景观。人们会在这里散步、慢跑、骑行，享受运动的乐趣和自然的美好',
        'major_scene': 'nature',
        'keywords': '步道 散步 慢跑 骑行 运动 自然'
    },
    'riverside': {
        'name': '河边',
        'description': '清澈的河边，河水缓缓流淌。人们会在这里散步、钓鱼、看风景，享受河边的宁静和清新',
        'major_scene': 'nature',
        'keywords': '河边 河水 散步 钓鱼 风景 清新'
    },
    'beach': {
        'name': '海滩',
        'description': '美丽的海滩，金色的沙滩和蔚蓝的海水。人们会在这里游泳、晒太阳、玩沙，享受海边的浪漫和放松',
        'major_scene': 'nature',
        'keywords': '海滩 沙滩 海水 游泳 浪漫 放松'
    },
    'mountain_path': {
        'name': '山间小径',
        'description': '山间的小径，两旁是茂密的植被。人们会来这里徒步、登山，感受山间的清新和挑战',
        'major_scene': 'nature',
        'keywords': '山间小径 山间 徒步 登山 清新 挑战'
    },
    'sunset_point': {
        'name': '观日落点',
        'description': '最佳的观日落地点，视野开阔。傍晚时分，人们会来这里看日落，欣赏夕阳西下的美景，感受自然的壮丽',
        'major_scene': 'nature',
        'keywords': '观日落点 日落 夕阳 美景 壮丽 傍晚'
    },
    # 文化学习场景
    'public_library': {
        'name': '公共图书馆',
        'description': '安静的公共图书馆，藏书丰富，环境优雅。人们会来这里阅读、学习、借书，是知识的殿堂',
        'major_scene': 'cultural',
        'keywords': '公共图书馆 图书馆 阅读 学习 借书 知识'
    },
    'museum': {
        'name': '博物馆',
        'description': '充满历史文化的博物馆，各种珍贵的文物和展品。人们会来这里参观、学习历史，感受文化的厚重',
        'major_scene': 'cultural',
        'keywords': '博物馆 文物 展品 历史 文化 参观'
    },
    'art_gallery': {
        'name': '艺术馆',
        'description': '高雅的艺术馆，各种精美的艺术品和画作。人们会来这里欣赏艺术，感受艺术的魅力和美感',
        'major_scene': 'cultural',
        'keywords': '艺术馆 艺术 艺术品 画作 欣赏 美感'
    },
    'concert_hall': {
        'name': '音乐厅',
        'description': '专业的音乐厅，音响效果极佳。人们会来这里听音乐会，享受音乐的魅力和艺术的熏陶',
        'major_scene': 'cultural',
        'keywords': '音乐厅 音乐会 音乐 艺术 音响 享受'
    },
    'exhibition_hall': {
        'name': '展览馆',
        'description': '宽敞的展览馆，各种主题展览在这里举办。人们会来这里参观展览，了解不同的文化和知识',
        'major_scene': 'cultural',
        'keywords': '展览馆 展览 主题 文化 知识 参观'
    },
    'cultural_center': {
        'name': '文化中心',
        'description': '综合性的文化中心，有各种文化活动和学习课程。人们会来这里参加活动、学习技能，是文化交流的场所',
        'major_scene': 'cultural',
        'keywords': '文化中心 文化活动 学习 课程 交流 技能'
    },
    'independent_bookstore': {
        'name': '独立书店',
        'description': '温馨的独立书店，有独特的选书品味和阅读氛围。爱书之人会来这里淘书、阅读、参加读书会，是文化爱好者的聚集地',
        'major_scene': 'cultural',
        'keywords': '独立书店 书店 选书 阅读 读书会 文化'
    },
    'theater': {
        'name': '剧院',
        'description': '专业的剧院，有精彩的戏剧和演出。人们会来这里观看演出，感受戏剧的魅力和艺术的感染力',
        'major_scene': 'cultural',
        'keywords': '剧院 戏剧 演出 观看 艺术 感染力'
    },
    'gallery': {
        'name': '画廊',
        'description': '精致的画廊，展示各种艺术作品。艺术爱好者会来这里欣赏画作，感受艺术的魅力和创作的灵感',
        'major_scene': 'cultural',
        'keywords': '画廊 画作 艺术 欣赏 创作 灵感'
    },
    'reading_room': {
        'name': '阅览室',
        'description': '安静的阅览室，有舒适的座位和良好的阅读环境。人们会来这里阅读、学习，享受阅读的宁静和专注',
        'major_scene': 'cultural',
        'keywords': '阅览室 阅读 学习 安静 专注 环境'
    },
    'workshop': {
        'name': '工作坊',
        'description': '专业的工作坊，有各种手工和创作活动。人们会来这里学习技能、创作作品，体验手工的乐趣',
        'major_scene': 'cultural',
        'keywords': '工作坊 手工 创作 学习 技能 乐趣'
    },
    'studio': {
        'name': '工作室',
        'description': '艺术工作室，有各种创作工具和材料。艺术家和爱好者会来这里创作、交流，是艺术创作的场所',
        'major_scene': 'cultural',
        'keywords': '工作室 创作 工具 材料 艺术 交流'
    }
}

# 兼容性：保留SCENES用于向后兼容，但只包含小场景
SCENES = SUB_SCENES.copy()

# 为各个大场景添加开头事件（这些事件对应小场景）
# 要求：事件要具体、合理，场景可以重复但事件内容要不同

# school大场景开头事件
MAJOR_SCENES['school']['opening_events'] = [
    {
        'id': 'deskmate_assignment',
        'title': '成为同桌',
        'description': '新学期第一节课，班主任重新调整座位，将你安排和TA成为同桌。当TA搬着书本坐到旁边时，礼貌地向你点头微笑，这是你们第一次正式接触',
        'sub_scene': 'classroom'
    },
    {
        'id': 'borrow_pen',
        'title': '邻座借笔',
        'description': '数学课上，你发现笔没水了，正着急时，坐在旁边的TA主动递过来一支笔，轻声说"先用我的吧"。你接过笔时，注意到TA温和的笑容',
        'sub_scene': 'classroom'
    },
    {
        'id': 'library_same_book',
        'title': '图书馆同找一本书',
        'description': '在图书馆的书架前，你们同时伸手去拿同一本参考书。手碰到一起的瞬间，两人都有些尴尬，TA先松开了手，笑着说"你先看吧，我等等再借"',
        'sub_scene': 'library'
    },
    {
        'id': 'library_help_find',
        'title': '帮忙找书',
        'description': '你在图书馆的书架间寻找一本参考书，找了很久都没找到。这时TA走过来，问你在找什么，然后熟练地帮你找到了那本书，并告诉你"我经常来这里，比较熟悉"',
        'sub_scene': 'library'
    },
    {
        'id': 'cafeteria_queue_behind',
        'title': '食堂排队',
        'description': '午餐时间，你在食堂排队打饭，发现TA就排在你前面。轮到你时，你点的菜刚好卖完了，TA回头看到你失望的表情，主动把自己的菜分了一半给你',
        'sub_scene': 'cafeteria'
    },
    {
        'id': 'cafeteria_seat_share',
        'title': '拼桌用餐',
        'description': '食堂里人很多，你端着餐盘找不到座位。这时TA看到你，主动招手让你过去，说"这里还有位置，一起坐吧"。你们边吃边聊，发现有很多共同话题',
        'sub_scene': 'cafeteria'
    },
    {
        'id': 'playground_ball_return',
        'title': '操场捡球',
        'description': '体育课上，你打篮球时不小心把球打到了场外，球滚到了正在旁边休息的TA脚边。TA捡起球，微笑着把球抛回给你，还说了句"加油"',
        'sub_scene': 'playground'
    },
    {
        'id': 'playground_running_together',
        'title': '操场跑步',
        'description': '傍晚时分，你在操场上跑步锻炼，发现TA也在跑道上慢跑。你们速度差不多，不知不觉并排跑了起来，TA主动和你打招呼，说"一起跑吧，有个伴"',
        'sub_scene': 'playground'
    },
    {
        'id': 'campus_path_umbrella',
        'title': '校园小径借伞',
        'description': '放学时突然下起了雨，你没带伞，正站在教学楼门口发愁。这时TA从后面走过来，看到你后主动把伞递过来，说"一起走吧，我送你到校门口"',
        'sub_scene': 'campus_path'
    },
    {
        'id': 'school_gate_bus_stop',
        'title': '校门口等车',
        'description': '在校门口的公交站等车时，你发现TA也在等同一路公交车。车来了但人很多，你们一起挤上车，TA站在你旁边，在拥挤的车厢里，你们有了第一次近距离接触',
        'sub_scene': 'school_gate'
    }
]

# company大场景开头事件
MAJOR_SCENES['company']['opening_events'] = [
    {
        'id': 'new_colleague_intro',
        'title': '新同事介绍',
        'description': '部门会议上，经理向大家介绍新来的同事TA。TA站起来向大家打招呼，你注意到TA温和的笑容和专业的自我介绍，这是你们第一次正式见面',
        'sub_scene': 'meeting_room'
    },
    {
        'id': 'elevator_meet',
        'title': '电梯偶遇',
        'description': '早上上班时，你在电梯里遇到了TA。电梯里只有你们两个人，TA主动按了楼层按钮，并礼貌地问你"几楼？"，你们有了第一次简单的交流',
        'sub_scene': 'elevator'
    },
    {
        'id': 'coffee_corner_help',
        'title': '咖啡角帮忙',
        'description': '在公司的咖啡角，你正在冲咖啡时发现咖啡机卡住了。这时TA走过来，熟练地帮你解决了问题，笑着说"这个机器有时候会这样，我来帮你"',
        'sub_scene': 'coffee_corner'
    },
    {
        'id': 'lunch_table_share',
        'title': '午餐拼桌',
        'description': '公司食堂里人很多，你端着餐盘找不到座位。这时TA看到你，主动招手让你过去，说"这里还有位置，一起坐吧"。你们边吃边聊，发现是同一个部门的',
        'sub_scene': 'company_cafeteria'
    },
    {
        'id': 'copy_room_assist',
        'title': '复印室协助',
        'description': '你在复印室打印文件时，打印机突然卡纸了。你正着急时，TA走过来帮你解决了问题，并告诉你"这个打印机经常卡纸，下次遇到可以找我"',
        'sub_scene': 'copy_room'
    },
    {
        'id': 'parking_lot_encounter',
        'title': '停车场偶遇',
        'description': '下班时，你在停车场取车，发现TA就停在你旁边的车位。TA看到你后主动打招呼，说"你也这个点下班啊"，你们简单聊了几句',
        'sub_scene': 'parking_lot'
    },
    {
        'id': 'training_together',
        'title': '一起培训',
        'description': '公司组织的新员工培训课上，你发现TA就坐在你旁边。培训间隙，TA主动和你交流培训内容，你们一起讨论，发现有很多共同话题',
        'sub_scene': 'training_room'
    },
    {
        'id': 'break_room_chat',
        'title': '休息室聊天',
        'description': '午休时间，你在休息室休息，发现TA也在那里。TA主动和你打招呼，你们聊起了工作，发现TA对工作很有见解，你们聊得很投缘',
        'sub_scene': 'break_room'
    },
    {
        'id': 'reception_visitor',
        'title': '前台接待',
        'description': '你到公司前台办事，发现TA也在那里。TA看到你后主动和你打招呼，并帮你处理了一些事情，你们有了第一次深入的交流',
        'sub_scene': 'reception'
    },
    {
        'id': 'balcony_break',
        'title': '阳台休息',
        'description': '工作累了，你到办公室阳台透透气，发现TA也在那里。TA看到你后主动和你聊天，你们一起看风景，聊工作，感觉很放松',
        'sub_scene': 'office_balcony'
    }
]

# dailylife大场景开头事件
MAJOR_SCENES['dailylife']['opening_events'] = [
    {
        'id': 'convenience_store_queue',
        'title': '便利店排队',
        'description': '晚上在便利店买东西，你发现TA就排在你前面。结账时TA发现忘带手机，你主动帮TA付了款，TA很感激，说"谢谢，我加你微信转给你"',
        'sub_scene': 'convenience_store'
    },
    {
        'id': 'residential_area_walk',
        'title': '小区散步',
        'description': '傍晚在小区里散步，你发现TA也在散步。你们速度差不多，不知不觉并排走了一段，TA主动和你打招呼，说"你也住这里啊"',
        'sub_scene': 'residential_area'
    },
    {
        'id': 'community_park_exercise',
        'title': '社区公园锻炼',
        'description': '早晨在社区公园锻炼，你发现TA也在那里跑步。你们在同一个区域锻炼，TA主动和你打招呼，说"一起锻炼吧，有个伴"',
        'sub_scene': 'community_park'
    },
    {
        'id': 'delivery_station_pickup',
        'title': '快递站取件',
        'description': '在快递站取快递时，你发现TA也在那里。你们同时找到了自己的包裹，TA看到你拿的包裹很重，主动帮你拿了一下，说"我帮你拿吧"',
        'sub_scene': 'delivery_station'
    },
    {
        'id': 'residential_gate_meet',
        'title': '小区门口相遇',
        'description': '下班回家时，你在小区门口遇到了TA。你们一起刷卡进门，TA主动和你聊天，发现你们住在同一栋楼，你们一起走回家',
        'sub_scene': 'residential_gate'
    },
    {
        'id': 'pet_shop_encounter',
        'title': '宠物店偶遇',
        'description': '在宠物店给宠物买食物时，你发现TA也在那里。TA看到你后主动和你打招呼，你们聊起了宠物，发现都很喜欢小动物，聊得很开心',
        'sub_scene': 'pet_shop'
    },
    {
        'id': 'supermarket_shopping',
        'title': '超市购物',
        'description': '周末在超市购物，你发现TA也在那里。你们在同一个货架前选商品，TA主动和你交流商品的选择，你们一起逛了超市',
        'sub_scene': 'supermarket'
    },
    {
        'id': 'pharmacy_consultation',
        'title': '药店咨询',
        'description': '在药店买药时，你发现TA也在那里咨询。药师在给TA介绍药品时，你也听到了，TA主动和你分享经验，你们聊起了健康话题',
        'sub_scene': 'pharmacy'
    },
    {
        'id': 'bakery_morning',
        'title': '面包店买早餐',
        'description': '早晨在面包店买早餐，你发现TA也在那里。你们同时看中了最后一个面包，TA主动让给了你，说"你先买吧，我等等"',
        'sub_scene': 'bakery'
    },
    {
        'id': 'fruit_stand_purchase',
        'title': '水果摊买水果',
        'description': '下班路上在水果摊买水果，你发现TA也在那里。你们一起挑选水果，TA主动和你交流哪种水果好吃，你们聊得很愉快',
        'sub_scene': 'fruit_stand'
    }
]

# leisure大场景开头事件
MAJOR_SCENES['leisure']['opening_events'] = [
    {
        'id': 'shopping_mall_encounter',
        'title': '购物中心偶遇',
        'description': '周末在购物中心逛街，你发现TA也在那里。你们在同一个店铺里看商品，TA主动和你交流，发现你们都喜欢同一个品牌，聊得很投缘',
        'sub_scene': 'shopping_mall'
    },
    {
        'id': 'cinema_same_movie',
        'title': '电影院同场',
        'description': '在电影院看电影，你发现TA就坐在你旁边。电影开始前，你们简单聊了几句，发现都喜欢这部电影，你们一起享受了观影时光',
        'sub_scene': 'cinema'
    },
    {
        'id': 'arcade_game_together',
        'title': '游戏厅一起玩',
        'description': '在游戏厅玩游戏时，你发现TA也在那里。TA看到你在玩一个游戏，主动过来和你一起玩，你们配合得很好，玩得很开心',
        'sub_scene': 'arcade'
    },
    {
        'id': 'ktv_room_share',
        'title': 'KTV拼房',
        'description': '在KTV唱歌时，你发现隔壁房间的TA也在唱歌。你们在走廊里遇到，TA主动邀请你一起唱，你们一起唱了几首歌，气氛很愉快',
        'sub_scene': 'ktv'
    },
    {
        'id': 'amusement_park_queue',
        'title': '游乐园排队',
        'description': '在游乐园排队玩项目时，你发现TA就排在你前面。你们一起排队聊天，发现都喜欢刺激的项目，你们一起玩了几个项目',
        'sub_scene': 'amusement_park'
    },
    {
        'id': 'aquarium_visit',
        'title': '水族馆参观',
        'description': '在水族馆参观时，你发现TA也在那里。你们在同一个水族箱前观赏，TA主动和你交流海洋生物的知识，你们一起参观了水族馆',
        'sub_scene': 'aquarium'
    },
    {
        'id': 'zoo_tour',
        'title': '动物园游览',
        'description': '在动物园游览时，你发现TA也在那里。你们在同一个动物展区前观看，TA主动和你交流动物的习性，你们一起游览了动物园',
        'sub_scene': 'zoo'
    },
    {
        'id': 'escape_room_team',
        'title': '密室逃脱组队',
        'description': '在密室逃脱店，你发现TA也在那里。你们都需要组队，TA主动邀请你一起组队，你们一起解谜，配合得很好',
        'sub_scene': 'escape_room'
    },
    {
        'id': 'board_game_cafe_play',
        'title': '桌游吧一起玩',
        'description': '在桌游吧，你发现TA也在那里。你们都需要组队玩游戏，TA主动邀请你一起玩，你们一起玩了几个桌游，玩得很开心',
        'sub_scene': 'board_game_cafe'
    },
    {
        'id': 'bowling_together',
        'title': '保龄球一起打',
        'description': '在保龄球馆，你发现TA也在那里。你们都需要组队，TA主动邀请你一起打，你们一起打了几局，玩得很愉快',
        'sub_scene': 'bowling_alley'
    }
]

# nature大场景开头事件
MAJOR_SCENES['nature']['opening_events'] = [
    {
        'id': 'city_park_walk',
        'title': '城市公园散步',
        'description': '周末在城市公园散步，你发现TA也在那里。你们在同一个区域散步，TA主动和你打招呼，说"一起走走吧"',
        'sub_scene': 'city_park'
    },
    {
        'id': 'lakeside_fishing',
        'title': '湖边钓鱼',
        'description': '在湖边钓鱼时，你发现TA也在那里。你们在同一个区域钓鱼，TA主动和你交流钓鱼技巧，你们一起享受了钓鱼的乐趣',
        'sub_scene': 'lakeside'
    },
    {
        'id': 'hilltop_sunrise',
        'title': '山顶看日出',
        'description': '早晨在山顶看日出，你发现TA也在那里。你们在同一个观景台等待日出，TA主动和你聊天，你们一起欣赏了美丽的日出',
        'sub_scene': 'hilltop_view'
    },
    {
        'id': 'forest_path_hiking',
        'title': '森林小径徒步',
        'description': '在森林小径徒步时，你发现TA也在那里。你们在同一个路段徒步，TA主动和你打招呼，你们一起走了一段路，聊得很愉快',
        'sub_scene': 'forest_path'
    },
    {
        'id': 'flower_garden_photo',
        'title': '花海拍照',
        'description': '在花海拍照时，你发现TA也在那里。你们在同一个区域拍照，TA主动帮你拍照，你们互相帮忙拍照，聊得很开心',
        'sub_scene': 'flower_garden'
    },
    {
        'id': 'lawn_picnic',
        'title': '草坪野餐',
        'description': '在草坪野餐时，你发现TA也在那里。你们在同一个区域野餐，TA主动和你打招呼，你们一起分享了食物，聊得很愉快',
        'sub_scene': 'lawn'
    },
    {
        'id': 'pavilion_rest',
        'title': '凉亭休息',
        'description': '在凉亭休息时，你发现TA也在那里。你们在同一个凉亭休息，TA主动和你聊天，你们一起享受了宁静的时光',
        'sub_scene': 'pavilion'
    },
    {
        'id': 'trail_running',
        'title': '步道跑步',
        'description': '在步道跑步时，你发现TA也在那里。你们速度差不多，不知不觉并排跑了起来，TA主动和你打招呼，你们一起跑了很久',
        'sub_scene': 'trail'
    },
    {
        'id': 'riverside_walk',
        'title': '河边散步',
        'description': '在河边散步时，你发现TA也在那里。你们在同一个区域散步，TA主动和你聊天，你们一起享受了河边的宁静',
        'sub_scene': 'riverside'
    },
    {
        'id': 'sunset_watching',
        'title': '观日落',
        'description': '傍晚在观日落点看日落，你发现TA也在那里。你们在同一个位置等待日落，TA主动和你聊天，你们一起欣赏了美丽的日落',
        'sub_scene': 'sunset_point'
    }
]

# cultural大场景开头事件
MAJOR_SCENES['cultural']['opening_events'] = [
    {
        'id': 'public_library_reading',
        'title': '公共图书馆阅读',
        'description': '在公共图书馆阅读时，你发现TA就坐在你旁边。你们在同一个区域阅读，TA主动和你打招呼，你们一起享受了阅读的宁静',
        'sub_scene': 'public_library'
    },
    {
        'id': 'museum_visit',
        'title': '博物馆参观',
        'description': '在博物馆参观时，你发现TA也在那里。你们在同一个展区参观，TA主动和你交流文物的历史，你们一起参观了博物馆',
        'sub_scene': 'museum'
    },
    {
        'id': 'art_gallery_appreciation',
        'title': '艺术馆欣赏',
        'description': '在艺术馆欣赏画作时，你发现TA也在那里。你们在同一个画作前欣赏，TA主动和你交流艺术见解，你们一起欣赏了艺术',
        'sub_scene': 'art_gallery'
    },
    {
        'id': 'concert_hall_attend',
        'title': '音乐厅听音乐会',
        'description': '在音乐厅听音乐会时，你发现TA就坐在你旁边。音乐会开始前，你们简单聊了几句，发现都喜欢音乐，你们一起享受了音乐',
        'sub_scene': 'concert_hall'
    },
    {
        'id': 'exhibition_hall_tour',
        'title': '展览馆参观',
        'description': '在展览馆参观展览时，你发现TA也在那里。你们在同一个展区参观，TA主动和你交流展览内容，你们一起参观了展览',
        'sub_scene': 'exhibition_hall'
    },
    {
        'id': 'cultural_center_activity',
        'title': '文化中心活动',
        'description': '在文化中心参加活动时，你发现TA也在那里。你们参加同一个活动，TA主动和你交流，你们一起参加了活动，聊得很投缘',
        'sub_scene': 'cultural_center'
    },
    {
        'id': 'independent_bookstore_browse',
        'title': '独立书店淘书',
        'description': '在独立书店淘书时，你发现TA也在那里。你们在同一个书架前选书，TA主动和你交流书籍，你们一起淘书，聊得很开心',
        'sub_scene': 'independent_bookstore'
    },
    {
        'id': 'theater_show',
        'title': '剧院看演出',
        'description': '在剧院看演出时，你发现TA就坐在你旁边。演出开始前，你们简单聊了几句，发现都喜欢戏剧，你们一起享受了演出',
        'sub_scene': 'theater'
    },
    {
        'id': 'gallery_appreciation',
        'title': '画廊欣赏',
        'description': '在画廊欣赏画作时，你发现TA也在那里。你们在同一个画作前欣赏，TA主动和你交流艺术见解，你们一起欣赏了画作',
        'sub_scene': 'gallery'
    },
    {
        'id': 'reading_room_study',
        'title': '阅览室学习',
        'description': '在阅览室学习时，你发现TA就坐在你旁边。你们在同一个区域学习，TA主动和你打招呼，你们一起享受了学习的宁静',
        'sub_scene': 'reading_room'
    }
]

# 辅助函数：根据大场景获取所有小场景
def get_sub_scenes_by_major_scene(major_scene_id: str) -> list:
    """根据大场景ID获取所有小场景ID列表"""
    major_scene = MAJOR_SCENES.get(major_scene_id)
    if major_scene:
        return major_scene.get('sub_scenes', [])
    return []

# 辅助函数：根据小场景获取所属大场景
def get_major_scene_by_sub_scene(sub_scene_id: str) -> str:
    """根据小场景ID获取所属大场景ID"""
    sub_scene = SUB_SCENES.get(sub_scene_id)
    if sub_scene:
        return sub_scene.get('major_scene', 'school')
    return 'school'

# 辅助函数：获取大场景的关键词
def get_major_scene_keyword(major_scene_id: str) -> str:
    """获取大场景的关键词（用于生成）"""
    major_scene = MAJOR_SCENES.get(major_scene_id)
    if major_scene:
        return major_scene.get('keyword', '')
    return ''

