import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QProgressBar, QMessageBox, QDialog, QGridLayout, QTabWidget,
    QListWidget, QListWidgetItem, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from file_utils import FileUtils
from video_comparator import VideoComparator

class ScanThread(QThread):
    """扫描线程，用于在后台扫描文件属性"""
    finished = pyqtSignal(list)
    progress = pyqtSignal(int)
    
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
    
    def run(self):
        try:
            # 先获取所有文件路径，计算总数
            total_files = 0
            for root, dirs, files in os.walk(self.directory):
                total_files += len(files) + len(dirs)
            
            # 然后扫描并报告进度
            scanned = 0
            file_properties = []
            for root, dirs, files in os.walk(self.directory):
                # 处理文件
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    properties = FileUtils._get_single_file_properties(file_path)
                    file_properties.append(properties)
                    scanned += 1
                    self.progress.emit(int((scanned / total_files) * 100))
                
                # 处理目录
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    properties = FileUtils._get_single_file_properties(dir_path)
                    file_properties.append(properties)
                    scanned += 1
                    self.progress.emit(int((scanned / total_files) * 100))
            
            self.finished.emit(file_properties)
        except Exception as e:
            self.finished.emit([{"error": str(e)}])

class FileBrowserWidget(QWidget):
    """文件浏览标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        # 创建布局
        main_layout = QVBoxLayout(self)
        
        # 顶部控制栏
        control_layout = QHBoxLayout()
        
        self.dir_label = QLabel("选择目录:")
        control_layout.addWidget(self.dir_label)
        
        self.dir_path_label = QLabel("未选择")
        self.dir_path_label.setMinimumWidth(400)
        control_layout.addWidget(self.dir_path_label)
        
        self.select_dir_btn = QPushButton("浏览")
        self.select_dir_btn.clicked.connect(self.select_directory)
        control_layout.addWidget(self.select_dir_btn)
        
        self.scan_btn = QPushButton("扫描")
        self.scan_btn.clicked.connect(self.scan_directory)
        self.scan_btn.setEnabled(False)
        control_layout.addWidget(self.scan_btn)
        
        main_layout.addLayout(control_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "路径", "名称", "类型", "大小", "权限", "最后修改时间", "扩展名"
        ])
        # 设置列宽 - 允许用户手动调整
        header = self.table.horizontalHeader()
        # 设置为交互式，允许用户手动调整列宽
        for i in range(7):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        # 初始时自动调整所有列宽以适应内容
        self.table.resizeColumnsToContents()
        # 确保表格能自适应窗口大小
        main_layout.addWidget(self.table)
    
    def select_directory(self):
        """选择目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择目录", "E:\\电报下载"
        )
        if directory:
            self.directory = directory
            self.dir_path_label.setText(directory)
            self.scan_btn.setEnabled(True)
            # 获取主窗口的状态栏
            main_window = self.parent().parent()
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(f"已选择目录: {directory}")
    
    def scan_directory(self):
        """扫描目录"""
        if not hasattr(self, 'directory'):
            QMessageBox.warning(self, "警告", "请先选择目录")
            return
        
        # 清空表格
        self.table.setRowCount(0)
        # 获取主窗口的状态栏
        main_window = self.parent().parent()
        if hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage("正在扫描...")
        self.scan_btn.setEnabled(False)
        self.select_dir_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 启动扫描线程
        self.scan_thread = ScanThread(self.directory)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.progress.connect(self.on_progress_update)
        self.scan_thread.start()
    
    def on_progress_update(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def on_scan_finished(self, file_properties):
        """扫描完成处理"""
        self.scan_btn.setEnabled(True)
        self.select_dir_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # 获取主窗口的状态栏
        main_window = self.parent().parent()
        
        if not file_properties:
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage("扫描完成，无文件")
            return
        
        if "error" in file_properties[0]:
            QMessageBox.critical(self, "错误", f"扫描失败: {file_properties[0]['error']}")
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage("扫描失败")
            return
        
        # 填充表格
        self.table.setRowCount(len(file_properties))
        
        for row, properties in enumerate(file_properties):
            # 路径
            path_item = QTableWidgetItem(properties.get("path", ""))
            self.table.setItem(row, 0, path_item)
            
            # 名称
            name_item = QTableWidgetItem(properties.get("name", ""))
            self.table.setItem(row, 1, name_item)
            
            # 类型
            type_item = QTableWidgetItem("目录" if properties.get("is_directory", False) else "文件")
            self.table.setItem(row, 2, type_item)
            
            # 大小
            size_item = QTableWidgetItem(str(properties.get("size", 0)) + " 字节")
            self.table.setItem(row, 3, size_item)
            
            # 权限
            mode_str = properties.get("mode_str", "")
            perm_item = QTableWidgetItem(mode_str)
            self.table.setItem(row, 4, perm_item)
            
            # 最后修改时间
            mtime = properties.get("mtime", "")
            mtime_item = QTableWidgetItem(str(mtime))
            self.table.setItem(row, 5, mtime_item)
            
            # 扩展名
            extension = properties.get("file_extension", "") if not properties.get("is_directory", False) else ""
            ext_item = QTableWidgetItem(extension)
            self.table.setItem(row, 6, ext_item)
        
        # 填充完成后，自动调整列宽以适应内容
        self.table.resizeColumnsToContents()
        
        if hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(f"扫描完成，找到 {len(file_properties)} 个文件/目录")

class FindDuplicatesThread(QThread):
    """查找重复视频的线程"""
    finished = pyqtSignal(list)
    progress = pyqtSignal(int)
    
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
    
    def run(self):
        try:
            # 收集所有视频文件
            video_files = []
            video_extensions = [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"]
            
            for root, dirs, files in os.walk(self.directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        video_files.append(os.path.join(root, file))
            
            total_files = len(video_files)
            # 计算每个视频的哈希值
            hash_to_files = {}
            
            for i, video_file in enumerate(video_files):
                try:
                    file_hash = VideoComparator.calculate_file_hash(video_file)
                    if file_hash not in hash_to_files:
                        hash_to_files[file_hash] = []
                    hash_to_files[file_hash].append(video_file)
                    # 发送进度
                    progress = int((i + 1) / total_files * 100)
                    self.progress.emit(progress)
                except Exception as e:
                    print(f"处理文件 {video_file} 时出错: {str(e)}")
            
            # 提取重复的视频组
            duplicate_groups = [files for files in hash_to_files.values() if len(files) > 1]
            
            self.finished.emit(duplicate_groups)
        except Exception as e:
            self.finished.emit([{"error": str(e)}])

class VideoComparatorWidget(QWidget):
    """视频比较标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        # 创建布局
        main_layout = QVBoxLayout(self)
        
        # 标签
        title_label = QLabel("重复视频查找")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # 目录选择区域
        dir_layout = QHBoxLayout()
        dir_label = QLabel("选择目录:")
        self.dir_path_label = QLabel("未选择")
        self.dir_path_label.setStyleSheet("border: 1px solid #ccc; padding: 5px; background-color: #f0f0f0;")
        self.dir_path_label.setMinimumWidth(400)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_directory)
        
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_path_label)
        dir_layout.addWidget(browse_btn)
        main_layout.addLayout(dir_layout)
        
        # 查找重复视频按钮
        self.find_duplicates_btn = QPushButton("查找重复视频")
        self.find_duplicates_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.find_duplicates_btn.clicked.connect(self.find_duplicate_videos)
        main_layout.addWidget(self.find_duplicates_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("margin: 10px 0;")
        main_layout.addWidget(self.progress_bar)
        
        # 结果显示区域
        result_layout = QVBoxLayout()
        result_title = QLabel("查找结果:")
        result_title.setStyleSheet("font-weight: bold;")
        result_layout.addWidget(result_title)
        
        # 使用 QListWidget 显示结果
        self.result_list = QListWidget()
        self.result_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f9f9f9;
                min-height: 300px;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:last-child {
                border-bottom: none;
            }
            QScrollBar:vertical {
                width: 10px;
                background: #f1f1f1;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a1a1a1;
            }
        """)
        self.result_list.setSelectionMode(QAbstractItemView.NoSelection)
        result_layout.addWidget(self.result_list)
        
        main_layout.addLayout(result_layout)
    

    
    def browse_directory(self):
        """浏览选择目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择目录", "E:\\电报下载"
        )
        if directory:
            self.directory = directory
            self.dir_path_label.setText(directory)
            # 清空结果列表
            self.result_list.clear()
    
    def find_duplicate_videos(self):
        """查找重复视频"""
        if not hasattr(self, 'directory'):
            QMessageBox.warning(self, "警告", "请先选择目录")
            return
        
        # 获取主窗口的状态栏
        main_window = self.parent().parent()
        if hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage("正在查找重复视频...")
        
        # 禁用按钮
        self.find_duplicates_btn.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 启动查找线程
        self.find_thread = FindDuplicatesThread(self.directory)
        self.find_thread.finished.connect(self.on_find_finished)
        self.find_thread.progress.connect(self.on_progress_update)
        self.find_thread.start()
    
    def on_progress_update(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def create_file_item(self, file_path):
        """创建带有删除按钮的文件列表项"""
        # 创建列表项
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 40))  # 固定高度，更加美观
        
        # 创建项的 widget
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        # 文件路径标签
        file_label = QLabel(file_path)
        file_label.setStyleSheet("font-size: 12px; color: #333;")
        file_label.setWordWrap(True)  # 自动换行
        file_label.setMinimumWidth(400)  # 最小宽度
        layout.addWidget(file_label, 1)  # 占满剩余空间
        
        # 添加伸缩空间，将按钮推到右侧
        layout.addStretch(1)
        
        # 按钮容器
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        
        # 预览按钮
        preview_btn = QPushButton("预览")
        preview_btn.setStyleSheet("font-size: 11px; padding: 4px 12px; background-color: #2196f3; color: white; border: none; border-radius: 3px;")
        preview_btn.setFixedSize(60, 24)  # 固定大小
        preview_btn.clicked.connect(lambda: self.preview_video(file_path))
        button_layout.addWidget(preview_btn)
        
        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("font-size: 11px; padding: 4px 12px; background-color: #f44336; color: white; border: none; border-radius: 3px;")
        delete_btn.setFixedSize(60, 24)  # 固定大小
        delete_btn.clicked.connect(lambda: self.delete_file(file_path))
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
        
        # 设置 widget 到列表项
        self.result_list.addItem(item)
        self.result_list.setItemWidget(item, widget)
    
    def preview_video(self, file_path):
        """预览视频 - 调用系统默认程序"""
        try:
            # 使用系统默认程序打开视频
            os.startfile(file_path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"预览失败: {str(e)}")
    
    def delete_file(self, file_path):
        """删除文件"""
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除文件 {os.path.basename(file_path)} 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                # 刷新结果列表
                self.find_duplicate_videos()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
    
    def on_find_finished(self, duplicate_groups):
        """查找完成处理"""
        # 启用按钮
        self.find_duplicates_btn.setEnabled(True)
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 获取主窗口的状态栏
        main_window = self.parent().parent()
        
        # 清空结果列表
        self.result_list.clear()
        
        if not duplicate_groups:
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage("查找完成，未找到重复视频")
            # 添加一个提示项
            item = QListWidgetItem("未找到重复视频")
            item.setForeground(Qt.gray)
            self.result_list.addItem(item)
            return
        
        if "error" in duplicate_groups[0]:
            error_message = duplicate_groups[0]["error"]
            QMessageBox.critical(self, "错误", f"查找失败: {error_message}")
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage("查找失败")
            # 添加错误提示项
            item = QListWidgetItem(f"查找失败: {error_message}")
            item.setForeground(Qt.red)
            self.result_list.addItem(item)
            return
        
        if duplicate_groups:
            # 显示找到的重复视频组
            for i, group in enumerate(duplicate_groups, 1):
                # 添加组标题
                group_item = QListWidgetItem(f"组 {i} (共 {len(group)} 个重复文件):")
                group_item.setForeground(Qt.blue)
                # QListWidgetItem 没有 setStyleSheet 方法，只设置前景色
                self.result_list.addItem(group_item)
                
                # 添加组内的文件
                for video in group:
                    self.create_file_item(video)
                
                # 添加分隔线
                separator = QListWidgetItem("-")
                separator.setForeground(Qt.lightGray)
                self.result_list.addItem(separator)
        
        if hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(f"查找完成，找到 {len(duplicate_groups)} 组重复视频")

class FileExplorer(QMainWindow):
    """文件资源管理器 GUI"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("文件工具")
        # 增大初始窗口大小，确保所有列都能显示
        self.setGeometry(100, 100, 1200, 700)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # 添加文件浏览标签页
        self.file_browser = FileBrowserWidget(self)
        self.tab_widget.addTab(self.file_browser, "文件浏览")
        
        # 添加重复视频查找标签页
        self.video_comparator = VideoComparatorWidget(self)
        self.tab_widget.addTab(self.video_comparator, "重复视频查找")
        
        # 底部状态栏
        self.statusBar().showMessage("就绪")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    explorer = FileExplorer()
    explorer.show()
    sys.exit(app.exec_())