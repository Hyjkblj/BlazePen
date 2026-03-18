"""主游戏入口"""
from typing import Dict
from database.db_manager import DatabaseManager
from database.vector_db import VectorDatabase
from game.character_creator import CharacterCreator
from game.story_engine import StoryEngine
from game.event_generator import EventGenerator
from data.scenes import SCENES


class Game:
    """游戏主类"""
    
    def __init__(self):
        # 初始化数据库
        self.db_manager = DatabaseManager()
        self.vector_db = VectorDatabase()
        
        # 初始化游戏组件
        self.character_creator = CharacterCreator(self.db_manager)
        self.event_generator = EventGenerator(self.vector_db, self.db_manager)
        self.story_engine = StoryEngine(self.event_generator, self.db_manager)
        
        self.character_id = None
    
    def create_character(self):
        """创建角色"""
        from data.player_choices import GENDER_OPTIONS, APPEARANCE_OPTIONS, PERSONALITY_OPTIONS
        
        print("=" * 50)
        print("欢迎来到无限流剧情游戏！")
        print("=" * 50)
        print("\n请创建你的角色：")
        
        # 输入角色名称
        name = input("角色名称: ").strip()
        if not name:
            name = "未命名角色"
        
        # 选择性别
        print("\n请选择性别：")
        for i, option in enumerate(GENDER_OPTIONS, 1):
            print(f"  {i}. {option}")
        while True:
            try:
                choice = int(input("请输入选项编号: "))
                if 1 <= choice <= len(GENDER_OPTIONS):
                    gender = GENDER_OPTIONS[choice - 1]
                    break
                else:
                    print(f"请输入1-{len(GENDER_OPTIONS)}之间的数字！")
            except ValueError:
                print("请输入有效的数字！")
        
        # 选择外观
        print("\n请选择外观：")
        for i, option in enumerate(APPEARANCE_OPTIONS, 1):
            print(f"  {i}. {option}")
        while True:
            try:
                choice = int(input("请输入选项编号: "))
                if 1 <= choice <= len(APPEARANCE_OPTIONS):
                    appearance = APPEARANCE_OPTIONS[choice - 1]
                    break
                else:
                    print(f"请输入1-{len(APPEARANCE_OPTIONS)}之间的数字！")
            except ValueError:
                print("请输入有效的数字！")
        
        # 选择性格
        print("\n请选择性格：")
        for i, option in enumerate(PERSONALITY_OPTIONS, 1):
            print(f"  {i}. {option}")
        while True:
            try:
                choice = int(input("请输入选项编号: "))
                if 1 <= choice <= len(PERSONALITY_OPTIONS):
                    personality = PERSONALITY_OPTIONS[choice - 1]
                    break
                else:
                    print(f"请输入1-{len(PERSONALITY_OPTIONS)}之间的数字！")
            except ValueError:
                print("请输入有效的数字！")
        
        print("\n正在随机抽取角色决定因素...")
        self.character_id = self.character_creator.create_character(
            name=name,
            gender=gender,
            appearance=appearance,
            personality=personality
        )
        
        # 显示角色信息
        character_info = self.character_creator.get_character_info(self.character_id)
        print("\n角色创建成功！")
        print(f"角色ID: {character_info['id']}")
        print(f"姓名: {character_info['name']}")
        print(f"性别: {character_info['gender']}")
        print(f"外观: {character_info['appearance']}")
        print(f"性格: {character_info['personality']}")
        print("\n随机抽取的决定因素：")
        for attr_type, attr_value in character_info['attributes'].items():
            print(f"  {attr_type}: {attr_value}")
    
    def select_scene(self):
        """选择场景"""
        print("\n" + "=" * 50)
        print("请选择场景：")
        print("1. 学校")
        print("=" * 50)
        
        choice = input("请输入场景编号 (默认1): ").strip() or "1"
        if choice == "1":
            return 'school'
        return 'school'
    
    def play_game(self):
        """开始游戏（支持多轮对话）"""
        if not self.character_id:
            print("请先创建角色！")
            return
        
        scene_id = self.select_scene()
        print(f"\n进入场景: {scene_id}")
        print("=" * 50)
        
        # 游戏循环
        game_finished = False
        while not game_finished:
            # 获取下一个事件（包含故事背景）
            event = self.story_engine.get_next_event(self.character_id, scene_id)
            
            # 显示事件标题和故事背景
            scene_name = ""
            if event.get('scene'):
                scene_info = SCENES.get(event['scene'], {})
                scene_name = scene_info.get('name', event['scene'])
            
            print(f"\n【{event['title']}】")
            if scene_name:
                print(f"📍 场景：{scene_name}")
            print("=" * 50)
            print(f"\n{event['story_background']}")
            print("\n" + "-" * 50)
            
            # 如果是结尾事件，特殊处理
            if event.get('ending_type'):
                # 结尾事件也进行多轮对话
                self._play_dialogue_rounds(event)
                print("\n" + "=" * 50)
                game_finished = True
                break
            
            # 进行多轮对话
            self._play_dialogue_rounds(event)
            
            # 保存事件到向量数据库
            self.story_engine.save_event_to_vector_db(self.character_id)
            
            print("\n" + "=" * 50)
            print("事件结束，进入下一个事件...")
            print("=" * 50)
            
            # 检查是否应该进入结尾
            if self.story_engine.is_game_finished():
                # 获取并显示结尾事件
                ending = self.story_engine.get_ending_event(self.character_id)
                print(f"\n【{ending['title']}】")
                print("=" * 50)
                print(f"\n{ending['story_background']}")
                print("\n" + "-" * 50)
                
                # 结尾事件的多轮对话
                self._play_dialogue_rounds(ending)
                print("\n" + "=" * 50)
                game_finished = True
        
        # 显示最终状态（显示全部12个状态值）
        states = self.db_manager.get_character_states(self.character_id)
        print("\n最终状态值：")
        print(f"  好感度: {states.favorability:.1f}")
        print(f"  信任度: {states.trust:.1f}")
        print(f"  敌意: {states.hostility:.1f}")
        print(f"  依赖度: {states.dependence:.1f}")
        print(f"  情绪: {states.emotion:.1f}")
        print(f"  压力: {states.stress:.1f}")
        print(f"  焦虑: {states.anxiety:.1f}")
        print(f"  快乐: {states.happiness:.1f}")
        print(f"  悲伤: {states.sadness:.1f}")
        print(f"  自信度: {states.confidence:.1f}")
        print(f"  主动度: {states.initiative:.1f}")
        print(f"  谨慎度: {states.caution:.1f}")
        print(f"  快乐: {states.happiness:.1f}")
        print(f"  自信度: {states.confidence:.1f}")
        print(f"  主动度: {states.initiative:.1f}")
        
        print("\n游戏结束！感谢游玩！")
    
    def _play_dialogue_rounds(self, event: Dict):
        """进行多轮对话（对话轮数由StoryEngine决定，确保有头有尾）"""
        dialogue_round = 0
        
        while True:
            dialogue_round += 1
            
            # 获取下一轮对话
            try:
                dialogue_data = self.story_engine.get_next_dialogue_round(self.character_id)
            except Exception as e:
                print(f"[错误] 生成对话失败: {e}")
                break
            
            # 显示角色对话
            print(f"\n[第{dialogue_round}轮对话]")
            character_dialogue = dialogue_data['character_dialogue']
            print(f"角色: {character_dialogue}")
            print()
            
            # 记录角色对话到对话历史
            self.story_engine.record_character_dialogue(character_dialogue)
            
            # 显示玩家选项（对话内容）
            print("你的回复：")
            for option in dialogue_data['player_options']:
                print(f"  {option['id']}. {option['text']}")
            
            # 玩家选择
            while True:
                try:
                    choice_num = int(input("\n请选择 (1-3): "))
                    if 1 <= choice_num <= 3:
                        selected_option = dialogue_data['player_options'][choice_num - 1]
                        break
                    else:
                        print("请输入1-3之间的数字！")
                except ValueError:
                    print("请输入有效的数字！")
            
            # 显示玩家选择
            print(f"\n你: {selected_option['text']}")
            
            # 处理选择（更新状态值并记录对话历史）
            self.story_engine.process_player_choice(self.character_id, selected_option)
            
            # 显示状态变化（显示所有状态值）
            if selected_option.get('state_changes'):
                print("\n[状态值变化]")
                state_names = {
                    'favorability': '好感度',
                    'trust': '信任度',
                    'hostility': '敌意',
                    'dependence': '依赖度',
                    'emotion': '情绪',
                    'stress': '压力',
                    'anxiety': '焦虑',
                    'happiness': '快乐',
                    'sadness': '悲伤',
                    'confidence': '自信度',
                    'initiative': '主动度',
                    'caution': '谨慎度'
                }
                for state, change in selected_option['state_changes'].items():
                    sign = "+" if change > 0 else ""
                    state_name = state_names.get(state, state)
                    print(f"  {state_name}: {sign}{change:.1f}")
            
            # 保存本轮对话到向量数据库（传递状态值变化）
            state_changes = selected_option.get('state_changes', {})
            self.story_engine.save_dialogue_round_to_vector_db(
                self.character_id, 
                dialogue_round,
                state_changes=state_changes
            )
            
            print("\n" + "-" * 50)
            
            # 判断是否继续对话
            # 由StoryEngine（AI）判断对话是否继续，确保对话完整、有收束
            if not self.story_engine.should_continue_dialogue(self.character_id):
                break


def main():
    """主函数"""
    game = Game()
    
    # 创建角色
    game.create_character()
    
    # 开始游戏
    input("\n按回车键开始游戏...")
    game.play_game()


if __name__ == '__main__':
    main()

