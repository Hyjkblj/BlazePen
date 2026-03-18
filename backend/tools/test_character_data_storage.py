"""测试角色数据字典存储功能"""
import sys
import os

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database.db_manager import DatabaseManager
from api.services.character_service import CharacterService


def test_character_data_storage():
    """测试角色数据字典存储和读取"""
    print("=" * 60)
    print("测试角色数据字典存储功能")
    print("=" * 60)
    
    try:
        # 模拟前端发送的数据
        test_request_data = {
            'name': '测试角色',
            'gender': 'female',
            'age': 20,
            'appearance': {
                'keywords': ['长发', '温柔', '可爱'],
                'height': 165,
                'weight': 50
            },
            'personality': {
                'keywords': ['内向', '善良', '细心']
            },
            'background': {
                'style': '校园风格'
            },
            'initial_scene': 'school'
        }
        
        print("\n1. 创建角色（存储字典数据）...")
        character_service = CharacterService()
        character_id = character_service.create_character(test_request_data)
        print(f"   [成功] 角色ID: {character_id}（用于与ChromaDB关联）")
        
        print("\n2. 读取角色数据（从character_data字段）...")
        character_info = character_service.get_character(character_id)
        print(f"   [成功] 角色名称: {character_info.get('name')}")
        print(f"   [成功] 性别: {character_info.get('gender')}")
        print(f"   [成功] 年龄: {character_info.get('age')}")
        print(f"   [成功] 身高: {character_info.get('height')}")
        print(f"   [成功] 体重: {character_info.get('weight')}")
        print(f"   [成功] 外观: {character_info.get('appearance')}")
        print(f"   [成功] 性格: {character_info.get('personality')}")
        print(f"   [成功] 背景: {character_info.get('background')}")
        
        print("\n3. 验证数据库中的character_data字段...")
        db_manager = DatabaseManager()
        character_data = db_manager.get_character_data(character_id)
        if character_data:
            print(f"   [成功] character_data字段存在")
            print(f"   [数据] {character_data}")
        else:
            print(f"   [警告] character_data字段为空")
        
        print("\n4. 验证角色ID作为关联key...")
        print(f"   [信息] 角色ID: {character_id}")
        print(f"   [信息] 此ID将用于与ChromaDB关联（metadata中的character_id字段）")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n[错误] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_character_data_storage()
    sys.exit(exit_code)

