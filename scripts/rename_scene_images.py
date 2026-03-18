"""重命名场景图片文件为 {scene_id}_{场景名称}.{ext} 格式"""
import os
import shutil
from pathlib import Path

# 场景名称到场景ID的映射
# 如果图片文件名不在这个映射中，将使用文件名本身作为scene_id
SCENE_NAME_TO_ID = {
    '咖啡厅': 'cafe_nearby',
    '餐厅': 'restaurant',
    '便利店': 'convenience_store',
    '公司': 'company',
    '动物园': 'zoo',
    '水族馆': 'aquarium',
    '游乐园': 'amusement_park',
    '羽毛球场': 'badminton_court',
    '自习室': 'study_room',
    '马路': 'street',
    # 从 scenes.py 中的场景名称映射
    '学校': 'school',
    '图书馆': 'library',
    '教室': 'classroom',
    '食堂': 'cafeteria',
    '操场': 'playground',
    '宿舍': 'dormitory',
    '校园小径': 'campus_path',
    '校门口': 'school_gate',
    '天台': 'rooftop',
    '体育馆': 'gym',
    '学校附近的咖啡厅': 'cafe_nearby',
    '书店': 'bookstore',
}

def rename_scene_images():
    """重命名场景图片文件"""
    # 获取场景图片目录
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent / 'backend'
    scenes_dir = backend_dir / 'images' / 'scenes'
    
    if not scenes_dir.exists():
        print(f"[错误] 场景图片目录不存在: {scenes_dir}")
        return
    
    print(f"[信息] 场景图片目录: {scenes_dir}")
    print(f"[信息] 开始重命名场景图片文件...\n")
    
    # 支持的图片扩展名
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    
    renamed_count = 0
    skipped_count = 0
    
    for filename in os.listdir(scenes_dir):
        file_path = scenes_dir / filename
        
        # 检查是否是图片文件
        if not file_path.is_file():
            continue
        
        # 检查扩展名
        ext = file_path.suffix.lower()
        if ext not in image_extensions:
            continue
        
        # 获取文件名（不含扩展名）
        name_without_ext = file_path.stem
        
        # 检查是否已经是正确格式 {scene_id}_{场景名称}.{ext}
        if '_' in name_without_ext:
            parts = name_without_ext.split('_', 1)
            if len(parts) == 2:
                # 已经是正确格式，跳过
                print(f"[跳过] {filename} 已经是正确格式")
                skipped_count += 1
                continue
        
        # 获取场景ID
        scene_name = name_without_ext
        scene_id = SCENE_NAME_TO_ID.get(scene_name, scene_name)
        
        # 如果场景名称不在映射中，使用场景名称本身作为scene_id
        # 但保持场景名称不变（用于显示）
        if scene_id == scene_name:
            # 场景名称作为scene_id，场景名称保持不变
            new_filename = f"{scene_id}_{scene_name}{ext}"
        else:
            # 使用映射的scene_id，场景名称保持不变
            new_filename = f"{scene_id}_{scene_name}{ext}"
        
        new_file_path = scenes_dir / new_filename
        
        # 检查新文件名是否已存在
        if new_file_path.exists():
            print(f"[警告] 目标文件已存在，跳过: {new_filename}")
            skipped_count += 1
            continue
        
        # 重命名文件
        try:
            file_path.rename(new_file_path)
            print(f"[成功] {filename} -> {new_filename}")
            renamed_count += 1
        except Exception as e:
            print(f"[错误] 重命名失败 {filename}: {e}")
    
    print(f"\n[完成] 重命名完成: {renamed_count} 个文件已重命名, {skipped_count} 个文件已跳过")

if __name__ == '__main__':
    rename_scene_images()
