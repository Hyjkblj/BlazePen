#!/usr/bin/env python3
"""
将场景图片从 characters 目录移动到 scenes 目录
"""

import os
import shutil
from pathlib import Path

def move_scene_images():
    """移动场景图片文件"""
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    
    # 源目录和目标目录
    characters_dir = backend_dir / 'images' / 'characters'
    scenes_dir = backend_dir / 'images' / 'scenes'
    
    # 确保目标目录存在
    scenes_dir.mkdir(parents=True, exist_ok=True)
    
    if not characters_dir.exists():
        print(f"[错误] 源目录不存在: {characters_dir}")
        return
    
    print(f"[信息] 源目录: {characters_dir}")
    print(f"[信息] 目标目录: {scenes_dir}")
    print(f"[信息] 开始移动场景图片文件...\n")
    
    # 查找所有场景图片文件（以 UNKNOWN_SCENE_ 开头）
    scene_files = list(characters_dir.glob("UNKNOWN_SCENE_*"))
    
    if not scene_files:
        print("[信息] 未找到场景图片文件（UNKNOWN_SCENE_*）")
        return
    
    print(f"[信息] 找到 {len(scene_files)} 个场景图片文件\n")
    
    moved_count = 0
    skipped_count = 0
    error_count = 0
    
    for file_path in scene_files:
        try:
            # 目标文件路径
            dest_path = scenes_dir / file_path.name
            
            # 如果目标文件已存在，跳过
            if dest_path.exists():
                print(f"[跳过] {file_path.name} 已存在于目标目录")
                skipped_count += 1
                continue
            
            # 移动文件
            shutil.move(str(file_path), str(dest_path))
            print(f"[移动] {file_path.name} -> {dest_path}")
            moved_count += 1
            
        except Exception as e:
            print(f"[错误] 移动文件失败 {file_path.name}: {e}")
            error_count += 1
    
    print(f"\n[完成] 移动完成:")
    print(f"  - 成功移动: {moved_count} 个文件")
    print(f"  - 跳过: {skipped_count} 个文件")
    print(f"  - 错误: {error_count} 个文件")

if __name__ == '__main__':
    move_scene_images()
