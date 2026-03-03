import os
import hashlib
import subprocess
from typing import Tuple, List, Dict, Any

class VideoComparator:
    """
    视频比较工具类，用于比较视频文件是否一致
    """
    
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = "md5") -> str:
        """
        计算文件的哈希值
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法，支持 md5, sha1, sha256
            
        Returns:
            文件的哈希值
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if algorithm not in ["md5", "sha1", "sha256"]:
            raise ValueError("不支持的哈希算法，支持的算法: md5, sha1, sha256")
        
        # 创建哈希对象
        if algorithm == "md5":
            hash_obj = hashlib.md5()
        elif algorithm == "sha1":
            hash_obj = hashlib.sha1()
        else:  # sha256
            hash_obj = hashlib.sha256()
        
        # 读取文件并计算哈希值
        with open(file_path, "rb") as f:
            # 分块读取，避免大文件占用过多内存
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def get_video_metadata(file_path: str) -> Dict[str, Any]:
        """
        获取视频文件的元数据
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            包含视频元数据的字典
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        metadata = {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "file_name": os.path.basename(file_path)
        }
        
        # 尝试使用 ffprobe 获取视频详细信息（如果可用）
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            import json
            ffprobe_data = json.loads(result.stdout)
            
            # 提取视频流信息
            for stream in ffprobe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    metadata["video_codec"] = stream.get("codec_name")
                    metadata["resolution"] = f"{stream.get('width')}x{stream.get('height')}"
                    metadata["duration"] = stream.get("duration")
                    metadata["fps"] = stream.get("r_frame_rate")
                    break
            
            # 提取格式信息
            format_data = ffprobe_data.get("format", {})
            metadata["format"] = format_data.get("format_name")
            metadata["bit_rate"] = format_data.get("bit_rate")
            
        except (subprocess.SubprocessError, ImportError):
            # 如果 ffprobe 不可用，只返回基本信息
            pass
        
        return metadata
    
    @staticmethod
    def compare_videos(video1: str, video2: str, method: str = "hash") -> Dict[str, Any]:
        """
        比较两个视频文件是否一致
        
        Args:
            video1: 第一个视频文件路径
            video2: 第二个视频文件路径
            method: 比较方法，支持 hash（哈希比较）或 metadata（元数据比较）
            
        Returns:
            比较结果字典
        """
        if not os.path.exists(video1):
            raise FileNotFoundError(f"第一个视频文件不存在: {video1}")
        
        if not os.path.exists(video2):
            raise FileNotFoundError(f"第二个视频文件不存在: {video2}")
        
        if method not in ["hash", "metadata"]:
            raise ValueError("不支持的比较方法，支持的方法: hash, metadata")
        
        result = {
            "video1": video1,
            "video2": video2,
            "method": method,
            "is_identical": False
        }
        
        if method == "hash":
            # 使用哈希值比较
            hash1 = VideoComparator.calculate_file_hash(video1)
            hash2 = VideoComparator.calculate_file_hash(video2)
            
            result["hash1"] = hash1
            result["hash2"] = hash2
            result["is_identical"] = (hash1 == hash2)
        
        elif method == "metadata":
            # 使用元数据比较
            metadata1 = VideoComparator.get_video_metadata(video1)
            metadata2 = VideoComparator.get_video_metadata(video2)
            
            result["metadata1"] = metadata1
            result["metadata2"] = metadata2
            
            # 比较关键元数据
            key_fields = ["file_size", "video_codec", "resolution", "duration"]
            all_match = True
            
            for field in key_fields:
                if metadata1.get(field) != metadata2.get(field):
                    all_match = False
                    break
            
            result["is_identical"] = all_match
        
        return result
    
    @staticmethod
    def find_duplicate_videos(directory: str) -> List[List[str]]:
        """
        查找目录中的重复视频文件
        
        Args:
            directory: 要搜索的目录
            
        Returns:
            重复视频组的列表，每个组包含重复的视频文件路径
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"不是一个目录: {directory}")
        
        # 收集所有视频文件
        video_files = []
        video_extensions = [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"]
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    video_files.append(os.path.join(root, file))
        
        # 计算每个视频的哈希值
        hash_to_files = {}
        
        for video_file in video_files:
            try:
                file_hash = VideoComparator.calculate_file_hash(video_file)
                if file_hash not in hash_to_files:
                    hash_to_files[file_hash] = []
                hash_to_files[file_hash].append(video_file)
            except Exception as e:
                print(f"处理文件 {video_file} 时出错: {str(e)}")
        
        # 提取重复的视频组
        duplicate_groups = [files for files in hash_to_files.values() if len(files) > 1]
        
        return duplicate_groups

if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) == 3:
        # 比较两个视频
        video1 = sys.argv[1]
        video2 = sys.argv[2]
        
        print("使用哈希方法比较:")
        result = VideoComparator.compare_videos(video1, video2, method="hash")
        print(f"视频1: {result['video1']}")
        print(f"视频2: {result['video2']}")
        print(f"哈希值1: {result['hash1']}")
        print(f"哈希值2: {result['hash2']}")
        print(f"是否相同: {'是' if result['is_identical'] else '否'}")
        
        print("\n使用元数据方法比较:")
        result = VideoComparator.compare_videos(video1, video2, method="metadata")
        print(f"视频1: {result['video1']}")
        print(f"视频2: {result['video2']}")
        print(f"是否相同: {'是' if result['is_identical'] else '否'}")
        
    elif len(sys.argv) == 2:
        # 查找目录中的重复视频
        directory = sys.argv[1]
        print(f"在目录 {directory} 中查找重复视频...")
        
        duplicate_groups = VideoComparator.find_duplicate_videos(directory)
        
        if duplicate_groups:
            print(f"找到 {len(duplicate_groups)} 组重复视频:")
            for i, group in enumerate(duplicate_groups, 1):
                print(f"\n组 {i}:")
                for video in group:
                    print(f"  - {video}")
        else:
            print("未找到重复视频")
    else:
        print("用法:")
        print("  比较两个视频: python video_comparator.py <video1> <video2>")
        print("  查找重复视频: python video_comparator.py <directory>")