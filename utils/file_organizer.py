import os
import re
import shutil
from typing import List, Dict, Tuple

class FileOrganizer:
    """
    文件分类工具类，用于根据正则表达式自动分类文件到文件夹
    """
    
    @staticmethod
    def organize_files(directory: str, rules: List[Tuple[str, str]]) -> Dict[str, List[str]]:
        """
        根据正则表达式规则组织文件
        
        Args:
            directory: 要组织的目录
            rules: 规则列表，每个规则是一个元组 (正则表达式, 目标文件夹)
            
        Returns:
            分类结果，键是目标文件夹，值是移动的文件列表
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"不是一个目录: {directory}")
        
        result = {}
        
        # 收集所有文件
        files = []
        for root, dirs, filenames in os.walk(directory):
            # 跳过子目录，只处理当前目录的文件
            if root == directory:
                for filename in filenames:
                    files.append(os.path.join(root, filename))
        
        # 处理每个文件
        for file_path in files:
            filename = os.path.basename(file_path)
            
            # 检查每个规则
            for pattern, target_folder in rules:
                # 使用 re.IGNORECASE 标志，不区分大小写
                if re.search(pattern, filename, re.IGNORECASE):
                    # 创建目标文件夹
                    target_path = os.path.join(directory, target_folder)
                    if not os.path.exists(target_path):
                        os.makedirs(target_path)
                    
                    # 移动文件
                    new_file_path = os.path.join(target_path, filename)
                    
                    # 处理文件名冲突
                    counter = 1
                    while os.path.exists(new_file_path):
                        name, ext = os.path.splitext(filename)
                        new_file_path = os.path.join(target_path, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    shutil.move(file_path, new_file_path)
                    
                    # 更新结果
                    if target_folder not in result:
                        result[target_folder] = []
                    result[target_folder].append(new_file_path)
                    
                    # 一个文件只匹配一个规则
                    break
        
        return result
    
    @staticmethod
    def get_default_rules() -> List[Tuple[str, str]]:
        """
        获取默认的分类规则
        
        Returns:
            默认规则列表
        """
        return [
            (r'\.(mp4|avi|mov|wmv|flv|mkv|webm)$', '视频'),
            (r'\.(jpg|jpeg|png|gif|bmp)$', '图片'),
            (r'\.(mp3|wav|flac|ogg|m4a)$', '音频'),
            (r'\.(doc|docx|pdf|txt|md)$', '文档'),
            (r'\.(zip|rar|7z|tar|gz)$', '压缩文件'),
            (r'\.(exe|msi|bat|sh)$', '可执行文件'),
            (r'\.(psd|ai|xd)$', '设计文件'),
            (r'\.(py|java|cpp|js|html|css)$', '代码文件'),
        ]