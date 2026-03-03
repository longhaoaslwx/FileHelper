import os
import stat
import datetime
from typing import List, Dict, Any

class FileUtils:
    """
    文件工具类，用于识别指定目录的所有文件属性
    """
    
    @staticmethod
    def get_file_properties(directory: str) -> List[Dict[str, Any]]:
        """
        获取指定目录下所有文件的属性
        
        Args:
            directory: 要扫描的目录路径
            
        Returns:
            包含文件属性的列表，每个元素是一个字典
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"不是一个目录: {directory}")
        
        file_properties = []
        
        for root, dirs, files in os.walk(directory):
            # 处理文件
            for file_name in files:
                file_path = os.path.join(root, file_name)
                properties = FileUtils._get_single_file_properties(file_path)
                file_properties.append(properties)
            
            # 处理目录
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                properties = FileUtils._get_single_file_properties(dir_path)
                file_properties.append(properties)
        
        return file_properties
    
    @staticmethod
    def _get_single_file_properties(file_path: str) -> Dict[str, Any]:
        """
        获取单个文件或目录的属性
        
        Args:
            file_path: 文件或目录的路径
            
        Returns:
            包含文件属性的字典
        """
        try:
            # 获取基本属性
            stat_info = os.stat(file_path)
            
            # 构建属性字典
            properties = {
                "path": file_path,
                "name": os.path.basename(file_path),
                "is_directory": os.path.isdir(file_path),
                "size": stat_info.st_size,
                "mode": stat_info.st_mode,
                "mode_str": stat.filemode(stat_info.st_mode),
                "uid": stat_info.st_uid,
                "gid": stat_info.st_gid,
                "atime": datetime.datetime.fromtimestamp(stat_info.st_atime),
                "mtime": datetime.datetime.fromtimestamp(stat_info.st_mtime),
                "ctime": datetime.datetime.fromtimestamp(stat_info.st_ctime),
                "permissions": {
                    "owner_read": bool(stat_info.st_mode & stat.S_IRUSR),
                    "owner_write": bool(stat_info.st_mode & stat.S_IWUSR),
                    "owner_execute": bool(stat_info.st_mode & stat.S_IXUSR),
                    "group_read": bool(stat_info.st_mode & stat.S_IRGRP),
                    "group_write": bool(stat_info.st_mode & stat.S_IWGRP),
                    "group_execute": bool(stat_info.st_mode & stat.S_IXGRP),
                    "others_read": bool(stat_info.st_mode & stat.S_IROTH),
                    "others_write": bool(stat_info.st_mode & stat.S_IWOTH),
                    "others_execute": bool(stat_info.st_mode & stat.S_IXOTH),
                }
            }
            
            # 如果是文件，添加文件类型信息
            if not properties["is_directory"]:
                properties["file_extension"] = os.path.splitext(file_path)[1]
            
            return properties
        except Exception as e:
            return {
                "path": file_path,
                "error": str(e)
            }
    
    @staticmethod
    def print_file_properties(directory: str):
        """
        打印指定目录下所有文件的属性
        
        Args:
            directory: 要扫描的目录路径
        """
        try:
            properties_list = FileUtils.get_file_properties(directory)
            print(f"\n目录 {directory} 下的文件属性:")
            print("-" * 80)
            
            for properties in properties_list:
                if "error" in properties:
                    print(f"路径: {properties['path']}")
                    print(f"错误: {properties['error']}")
                else:
                    print(f"路径: {properties['path']}")
                    print(f"名称: {properties['name']}")
                    print(f"类型: {'目录' if properties['is_directory'] else '文件'}")
                    if not properties['is_directory']:
                        print(f"扩展名: {properties.get('file_extension', '无')}")
                    print(f"大小: {properties['size']} 字节")
                    print(f"权限: {properties['mode_str']}")
                    print(f"最后修改时间: {properties['mtime']}")
                print("-" * 80)
                
        except Exception as e:
            print(f"错误: {str(e)}")

if __name__ == "__main__":
    # 测试代码
    test_dir = "E:\\电报下载"
    FileUtils.print_file_properties(test_dir)