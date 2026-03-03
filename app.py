import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QProgressBar, QMessageBox, QDialog, QGridLayout, QTabWidget,
    QListWidget, QListWidgetItem, QAbstractItemView, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from utils.file_utils import FileUtils
from utils.video_comparator import VideoComparator
from utils.file_organizer import FileOrganizer

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
        title_label = QLabel("视频查重")
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
        
        # 开始查重按钮
        self.find_duplicates_btn = QPushButton("开始查重")
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
        result_title = QLabel("查重结果:")
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
            main_window.statusBar().showMessage("正在查重...")
        
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
                main_window.statusBar().showMessage("查重完成，未找到重复视频")
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
            main_window.statusBar().showMessage(f"查重完成，找到 {len(duplicate_groups)} 组重复视频")

class FileOrganizerWidget(QWidget):
    """文件分类标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 初始化规则为默认规则
        self.rules = FileOrganizer.get_default_rules()
        # 加载配置文件
        self.load_config()
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        # 创建布局
        main_layout = QVBoxLayout(self)
        
        # 标签
        title_label = QLabel("文件分类")
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
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 规则方案选择
        scheme_layout = QHBoxLayout()
        scheme_label = QLabel("规则方案:")
        from PyQt5.QtWidgets import QComboBox
        self.scheme_combo = QComboBox()
        self.scheme_combo.addItems(["默认规则", "自定义规则"])
        # 连接信号处理
        self.scheme_combo.currentTextChanged.connect(self.on_scheme_changed)
        scheme_layout.addWidget(scheme_label)
        scheme_layout.addWidget(self.scheme_combo)
        button_layout.addLayout(scheme_layout)
        
        # 规则配置按钮
        self.config_btn = QPushButton("规则配置")
        self.config_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.config_btn.clicked.connect(self.open_rule_config)
        button_layout.addWidget(self.config_btn)
        
        # 分类按钮
        self.organize_btn = QPushButton("开始分类")
        self.organize_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.organize_btn.clicked.connect(self.organize_files)
        button_layout.addWidget(self.organize_btn)
        
        main_layout.addLayout(button_layout)
        
        # 结果显示区域
        result_layout = QVBoxLayout()
        result_title = QLabel("分类结果:")
        result_title.setStyleSheet("font-weight: bold;")
        result_layout.addWidget(result_title)
        
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
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        result_layout.addWidget(self.result_list)
        
        main_layout.addLayout(result_layout)
        
        # 设置规则方案
        if hasattr(self, 'scheme'):
            index = self.scheme_combo.findText(self.scheme)
            if index != -1:
                self.scheme_combo.setCurrentIndex(index)
    
    def browse_directory(self):
        """浏览选择目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择目录", "E:\电报下载"
        )
        if directory:
            self.directory = directory
            self.dir_path_label.setText(directory)
            self.result_list.clear()
    
    def on_scheme_changed(self, scheme):
        """规则方案变化处理"""
        if scheme == "默认规则":
            # 保存当前的自定义规则
            if hasattr(self, 'custom_rules'):
                self.custom_rules = self.rules
            # 加载默认规则
            self.rules = FileOrganizer.get_default_rules()
        else:
            # 恢复自定义规则
            if hasattr(self, 'custom_rules'):
                self.rules = self.custom_rules
            else:
                # 如果没有自定义规则，使用当前规则
                self.custom_rules = self.rules.copy()
        # 保存配置
        self.save_config()
    
    def open_rule_config(self):
        """打开规则配置对话框"""
        # 创建规则配置对话框
        dialog = QDialog(self)
        # 设置标题为规则方案名
        scheme = self.scheme_combo.currentText()
        dialog.setWindowTitle(f"规则配置 - {scheme}")
        dialog.setGeometry(300, 200, 800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # 规则列表
        rules_label = QLabel("当前规则:")
        rules_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(rules_label)
        
        self.rule_list = QListWidget()
        self.rule_list.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 支持多选
        self.rule_list.setStyleSheet("""
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
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        layout.addWidget(self.rule_list)
        
        # 加载规则
        self.load_rules()
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 编辑规则按钮
        edit_btn = QPushButton("编辑规则")
        edit_btn.clicked.connect(lambda: self.edit_rule(self.rule_list.currentRow()))
        button_layout.addWidget(edit_btn)
        
        # 添加规则按钮
        add_btn = QPushButton("添加规则")
        add_btn.clicked.connect(self.add_rule)
        button_layout.addWidget(add_btn)
        
        # 删除规则按钮
        delete_btn = QPushButton("删除规则")
        delete_btn.clicked.connect(self.delete_selected_rules)
        button_layout.addWidget(delete_btn)
        
        # 保存配置按钮
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_rules)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        # 显示非模态对话框
        dialog.show()
    
    def load_rules(self):
        """加载规则到列表"""
        # 清空列表
        self.rule_list.clear()
        
        # 添加到列表
        for pattern, folder in self.rules:
            item = QListWidgetItem(f"{pattern} → {folder}")
            self.rule_list.addItem(item)
    
    def edit_rule(self, index):
        """编辑规则"""
        if index < 0 or index >= len(self.rules):
            return
        
        # 获取当前规则
        pattern, folder = self.rules[index]
        
        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑规则")
        dialog.setGeometry(400, 300, 600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 规则类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("规则类型:")
        from PyQt5.QtWidgets import QComboBox
        self.rule_type = QComboBox()
        self.rule_type.addItems(["自定义正则表达式", "包含", "不包含", "后缀名"])
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.rule_type)
        layout.addLayout(type_layout)
        
        # 自定义正则表达式输入
        self.custom_pattern_widget = QWidget()
        self.custom_pattern_layout = QHBoxLayout(self.custom_pattern_widget)
        custom_pattern_label = QLabel("自定义正则表达式:")
        self.custom_pattern_input = QLineEdit(pattern)
        self.custom_pattern_layout.addWidget(custom_pattern_label)
        self.custom_pattern_layout.addWidget(self.custom_pattern_input)
        layout.addWidget(self.custom_pattern_widget)
        
        # 包含内容输入
        self.include_widget = QWidget()
        self.include_layout = QHBoxLayout(self.include_widget)
        include_label = QLabel("包含内容:")
        self.include_input = QLineEdit()
        self.include_layout.addWidget(include_label)
        self.include_layout.addWidget(self.include_input)
        self.include_widget.setVisible(False)
        layout.addWidget(self.include_widget)
        
        # 不包含内容输入
        self.exclude_widget = QWidget()
        self.exclude_layout = QHBoxLayout(self.exclude_widget)
        exclude_label = QLabel("不包含内容:")
        self.exclude_input = QLineEdit()
        self.exclude_layout.addWidget(exclude_label)
        self.exclude_layout.addWidget(self.exclude_input)
        self.exclude_widget.setVisible(False)
        layout.addWidget(self.exclude_widget)
        
        # 后缀名输入
        self.extension_widget = QWidget()
        self.extension_layout = QHBoxLayout(self.extension_widget)
        extension_label = QLabel("后缀名 (多个用逗号分隔):")
        self.extension_input = QLineEdit()
        self.extension_layout.addWidget(extension_label)
        self.extension_layout.addWidget(self.extension_input)
        self.extension_widget.setVisible(False)
        layout.addWidget(self.extension_widget)
        
        # 目标文件夹输入
        folder_layout = QHBoxLayout()
        folder_label = QLabel("目标文件夹:")
        self.folder_input = QLineEdit(folder)
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_input)
        layout.addLayout(folder_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # 规则类型变化处理
        def on_rule_type_changed():
            rule_type = self.rule_type.currentText()
            self.custom_pattern_widget.setVisible(rule_type == "自定义正则表达式")
            self.include_widget.setVisible(rule_type == "包含")
            self.exclude_widget.setVisible(rule_type == "不包含")
            self.extension_widget.setVisible(rule_type == "后缀名")
        
        self.rule_type.currentTextChanged.connect(on_rule_type_changed)
        
        # 初始化界面
        # 尝试解析当前正则表达式，确定规则类型
        if pattern.startswith("^") and pattern.endswith("$"):
            # 检查是否是后缀名规则
            if pattern.startswith("^.*\\.") and pattern.endswith("$"):
                ext_pattern = pattern[5:-1]
                if "|" in ext_pattern:
                    extensions = ext_pattern.split("|")
                    extension_text = ",".join([ext[1:] if ext.startswith("\\") else ext for ext in extensions])
                    self.rule_type.setCurrentText("后缀名")
                    self.extension_input.setText(extension_text)
                else:
                    self.rule_type.setCurrentText("自定义正则表达式")
            # 检查是否是包含规则
            elif pattern.startswith("^.*") and pattern.endswith(".*$"):
                include_text = pattern[3:-3]
                self.rule_type.setCurrentText("包含")
                self.include_input.setText(include_text)
            # 检查是否是不包含规则
            elif pattern.startswith("^(?!.*") and pattern.endswith(".*$)"):
                exclude_text = pattern[6:-4]
                self.rule_type.setCurrentText("不包含")
                self.exclude_input.setText(exclude_text)
            else:
                self.rule_type.setCurrentText("自定义正则表达式")
        else:
            self.rule_type.setCurrentText("自定义正则表达式")
        
        on_rule_type_changed()
        
        # 保存按钮点击事件
        def save_rule():
            rule_type = self.rule_type.currentText()
            new_folder = self.folder_input.text().strip()
            
            if not new_folder:
                QMessageBox.warning(dialog, "警告", "请输入目标文件夹")
                return
            
            if rule_type == "自定义正则表达式":
                new_pattern = self.custom_pattern_input.text().strip()
                if not new_pattern:
                    QMessageBox.warning(dialog, "警告", "请输入正则表达式")
                    return
            elif rule_type == "包含":
                include_text = self.include_input.text().strip()
                if not include_text:
                    QMessageBox.warning(dialog, "警告", "请输入包含内容")
                    return
                new_pattern = f"^.*{include_text}.*$"
            elif rule_type == "不包含":
                exclude_text = self.exclude_input.text().strip()
                if not exclude_text:
                    QMessageBox.warning(dialog, "警告", "请输入不包含内容")
                    return
                new_pattern = f"^(?!.*{exclude_text}).*$"
            elif rule_type == "后缀名":
                extension_text = self.extension_input.text().strip()
                if not extension_text:
                    QMessageBox.warning(dialog, "警告", "请输入后缀名")
                    return
                extensions = [ext.strip() for ext in extension_text.split(",")]
                ext_pattern = "|".join([f"\\.{ext}" for ext in extensions])
                new_pattern = f"^.*({ext_pattern})$"
            
            self.rules[index] = (new_pattern, new_folder)
            self.load_rules()  # 刷新列表
            dialog.accept()
        
        save_btn.clicked.connect(save_rule)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec_()
    
    def add_rule(self):
        """添加规则"""
        # 创建添加对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("添加规则")
        dialog.setGeometry(400, 300, 600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 规则类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("规则类型:")
        from PyQt5.QtWidgets import QComboBox
        rule_type = QComboBox()
        rule_type.addItems(["自定义正则表达式", "包含", "不包含", "后缀名"])
        type_layout.addWidget(type_label)
        type_layout.addWidget(rule_type)
        layout.addLayout(type_layout)
        
        # 自定义正则表达式输入
        custom_pattern_widget = QWidget()
        custom_pattern_layout = QHBoxLayout(custom_pattern_widget)
        custom_pattern_label = QLabel("自定义正则表达式:")
        custom_pattern_input = QLineEdit()
        custom_pattern_layout.addWidget(custom_pattern_label)
        custom_pattern_layout.addWidget(custom_pattern_input)
        layout.addWidget(custom_pattern_widget)
        
        # 包含内容输入
        include_widget = QWidget()
        include_layout = QHBoxLayout(include_widget)
        include_label = QLabel("包含内容:")
        include_input = QLineEdit()
        include_layout.addWidget(include_label)
        include_layout.addWidget(include_input)
        include_widget.setVisible(False)
        layout.addWidget(include_widget)
        
        # 不包含内容输入
        exclude_widget = QWidget()
        exclude_layout = QHBoxLayout(exclude_widget)
        exclude_label = QLabel("不包含内容:")
        exclude_input = QLineEdit()
        exclude_layout.addWidget(exclude_label)
        exclude_layout.addWidget(exclude_input)
        exclude_widget.setVisible(False)
        layout.addWidget(exclude_widget)
        
        # 后缀名输入
        extension_widget = QWidget()
        extension_layout = QHBoxLayout(extension_widget)
        extension_label = QLabel("后缀名 (多个用逗号分隔):")
        extension_input = QLineEdit()
        extension_layout.addWidget(extension_label)
        extension_layout.addWidget(extension_input)
        extension_widget.setVisible(False)
        layout.addWidget(extension_widget)
        
        # 目标文件夹输入
        folder_layout = QHBoxLayout()
        folder_label = QLabel("目标文件夹:")
        folder_input = QLineEdit()
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(folder_input)
        layout.addLayout(folder_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # 规则类型变化处理
        def on_rule_type_changed():
            current_type = rule_type.currentText()
            custom_pattern_widget.setVisible(current_type == "自定义正则表达式")
            include_widget.setVisible(current_type == "包含")
            exclude_widget.setVisible(current_type == "不包含")
            extension_widget.setVisible(current_type == "后缀名")
        
        rule_type.currentTextChanged.connect(on_rule_type_changed)
        on_rule_type_changed()  # 初始化显示
        
        # 保存按钮点击事件
        def save_rule():
            current_type = rule_type.currentText()
            folder = folder_input.text().strip()
            
            if not folder:
                QMessageBox.warning(dialog, "警告", "请输入目标文件夹")
                return
            
            if current_type == "自定义正则表达式":
                pattern = custom_pattern_input.text().strip()
                if not pattern:
                    QMessageBox.warning(dialog, "警告", "请输入正则表达式")
                    return
            elif current_type == "包含":
                include_text = include_input.text().strip()
                if not include_text:
                    QMessageBox.warning(dialog, "警告", "请输入包含内容")
                    return
                pattern = f"^.*{include_text}.*$"
            elif current_type == "不包含":
                exclude_text = exclude_input.text().strip()
                if not exclude_text:
                    QMessageBox.warning(dialog, "警告", "请输入不包含内容")
                    return
                pattern = f"^(?!.*{exclude_text}).*$"
            elif current_type == "后缀名":
                extension_text = extension_input.text().strip()
                if not extension_text:
                    QMessageBox.warning(dialog, "警告", "请输入后缀名")
                    return
                extensions = [ext.strip() for ext in extension_text.split(",")]
                ext_pattern = "|".join([f"\\.{ext}" for ext in extensions])
                pattern = f"^.*({ext_pattern})$"
            
            self.rules.append((pattern, folder))
            self.load_rules()  # 刷新列表
            dialog.accept()
        
        save_btn.clicked.connect(save_rule)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec_()
    
    def delete_selected_rules(self):
        """删除选中的规则"""
        selected_items = self.rule_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要删除的规则")
            return
        
        # 获取选中项的索引
        indexes = [self.rule_list.row(item) for item in selected_items]
        # 按降序排序，避免删除时索引变化
        indexes.sort(reverse=True)
        
        # 删除规则
        for index in indexes:
            self.rules.pop(index)
        
        # 刷新列表
        self.load_rules()
    
    def save_rules(self):
        """保存规则配置"""
        # 保存规则到custom_rules
        self.custom_rules = self.rules.copy()
        # 保存到配置文件
        self.save_config()
        QMessageBox.information(self, "提示", "规则配置已保存")
    
    def load_config(self):
        """加载配置文件"""
        config_file = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "custom_rules" in config:
                        self.custom_rules = config["custom_rules"]
                    if "scheme" in config:
                        self.scheme = config["scheme"]
            except Exception as e:
                print(f"加载配置文件失败: {e}")
    
    def save_config(self):
        """保存配置文件"""
        config_file = os.path.join(os.path.dirname(__file__), "config.json")
        try:
            config = {
                "custom_rules": self.custom_rules if hasattr(self, 'custom_rules') else [],
                "scheme": self.scheme_combo.currentText() if hasattr(self, 'scheme_combo') else "默认规则"
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def organize_files(self):
        """组织文件"""
        if not hasattr(self, 'directory'):
            QMessageBox.warning(self, "警告", "请先选择目录")
            return
        
        try:
            # 获取主窗口的状态栏
            main_window = self.parent().parent()
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage("正在分类文件...")
            
            # 清空结果列表
            self.result_list.clear()
            
            # 根据选择的规则方案决定使用的规则
            selected_scheme = self.scheme_combo.currentText()
            if selected_scheme == "默认规则":
                # 使用默认规则
                rules = FileOrganizer.get_default_rules()
            else:
                # 使用自定义规则
                rules = self.rules
            
            # 组织文件
            result = FileOrganizer.organize_files(self.directory, rules)
            
            # 显示结果
            if result:
                for folder, files in result.items():
                    # 添加文件夹标题
                    folder_item = QListWidgetItem(f"文件夹: {folder} (共 {len(files)} 个文件)")
                    folder_item.setForeground(Qt.blue)
                    self.result_list.addItem(folder_item)
                    
                    # 添加文件列表
                    for file in files:
                        file_item = QListWidgetItem(f"  - {os.path.basename(file)}")
                        self.result_list.addItem(file_item)
                    
                    # 添加分隔线
                    separator = QListWidgetItem("-")
                    separator.setForeground(Qt.lightGray)
                    self.result_list.addItem(separator)
            else:
                item = QListWidgetItem("没有文件需要分类")
                item.setForeground(Qt.gray)
                self.result_list.addItem(item)
            
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage("分类完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分类失败: {str(e)}")
            main_window = self.parent().parent()
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage("分类失败")

class FileExplorer(QMainWindow):
    """文件资源管理器 GUI"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("文件管理助手")
        # 增大初始窗口大小，确保所有列都能显示
        self.setGeometry(100, 100, 1200, 700)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # 添加视频查重标签页
        self.video_comparator = VideoComparatorWidget(self)
        self.tab_widget.addTab(self.video_comparator, "视频查重")
        
        # 添加文件分类标签页
        self.file_organizer = FileOrganizerWidget(self)
        self.tab_widget.addTab(self.file_organizer, "文件分类")
        
        # 底部状态栏
        self.statusBar().showMessage("就绪")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    explorer = FileExplorer()
    explorer.show()
    sys.exit(app.exec_())