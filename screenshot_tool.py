#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QWidget,
                             QPushButton, QVBoxLayout, QLabel, QMainWindow, QHBoxLayout)
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QCursor, QColor, QImage
import io


class DraggableWidget(QWidget):
    """可拖动的小部件基类"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.drag_position = QPoint()

    def mousePressEvent(self, event):
        """鼠标/触摸按下 - 开始拖动"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击在按钮上
            child = self.childAt(event.pos())
            if isinstance(child, QPushButton):
                # 如果点击的是按钮，让按钮处理事件
                super().mousePressEvent(event)
                return

            # 否则开始拖动
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标/触摸移动 - 拖动"""
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标/触摸释放 - 停止拖动"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()


class DraggableToolbar(DraggableWidget):
    """可拖动的工具栏"""
    pass


class DraggableLabel(QLabel):
    """可拖动的标签"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.dragging = False
        self.drag_position = QPoint()

    def mousePressEvent(self, event):
        """鼠标/触摸按下 - 开始拖动"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标/触摸移动 - 拖动标签"""
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标/触摸释放 - 停止拖动"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.OpenHandCursor)
            event.accept()


class ScreenshotEditor(QMainWindow):
    """截图编辑窗口，支持画笔标注"""
    closed = pyqtSignal()

    def __init__(self, pixmap):
        super().__init__()
        self.pixmap = pixmap
        self.drawing = False
        self.last_point = QPoint()
        self.pen_width = 3
        self.pen_color = Qt.red
        self.draw_mode = "line"  # "line" or "arrow"
        self.arrow_start = QPoint()
        self.arrow_end = QPoint()
        self.temp_arrow_drawing = False

        self.setWindowTitle("截图编辑")
        self.setWindowState(Qt.WindowFullScreen)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        # 创建画布
        self.canvas = QPixmap(self.pixmap)

        # 创建可拖动的提示标签
        self.hint_label = DraggableLabel("✏️ 手指拖动画红线标注 | 按住此框可移动", self)
        self.hint_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 15px;
            border: 2px dashed rgba(150, 150, 150, 100);
        """)
        self.hint_label.adjustSize()
        # 放置在右上角
        screen = QApplication.primaryScreen().geometry()
        self.hint_label.move(screen.width() - self.hint_label.width() - 10, 10)
        self.hint_label.setCursor(Qt.OpenHandCursor)

        # 创建底部按钮工具栏
        self.create_toolbar()

        self.setCursor(Qt.CrossCursor)

    def create_toolbar(self):
        """创建可拖动的触屏按钮工具栏"""
        # 获取屏幕尺寸
        screen = QApplication.primaryScreen().geometry()

        # 创建可拖动的按钮容器
        self.toolbar = DraggableToolbar(self)
        self.toolbar.setStyleSheet("""
            DraggableToolbar {
                background-color: rgba(40, 40, 40, 220);
                border-radius: 10px;
                border: 2px dashed rgba(100, 100, 100, 150);
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                min-width: 150px;
                min-height: 60px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#cancelBtn {
                background-color: #f44336;
            }
            QPushButton#cancelBtn:hover {
                background-color: #da190b;
            }
            QPushButton#cancelBtn:pressed {
                background-color: #c1170a;
            }
            QLabel {
                color: #aaa;
                font-size: 12px;
            }
        """)

        # 创建垂直布局（添加拖动提示）
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 10, 15, 15)
        main_layout.setSpacing(8)

        # 添加拖动提示
        drag_hint = QLabel("⋮⋮ 按住空白处可拖动 ⋮⋮")
        drag_hint.setAlignment(Qt.AlignCenter)
        drag_hint.setStyleSheet("color: #888; font-size: 11px;")
        main_layout.addWidget(drag_hint)

        # 创建按钮的水平布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        # 画线按钮
        self.line_btn = QPushButton("✏️ 画线")
        self.line_btn.clicked.connect(self.set_line_mode)
        btn_layout.addWidget(self.line_btn)

        # 画箭头按钮
        self.arrow_btn = QPushButton("➡️ 画箭头")
        self.arrow_btn.clicked.connect(self.set_arrow_mode)
        self.arrow_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                min-width: 150px;
                min-height: 60px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #0a6fc2;
            }
        """)
        btn_layout.addWidget(self.arrow_btn)

        # 保存按钮
        self.save_btn = QPushButton("✓ 保存")
        self.save_btn.clicked.connect(self.save_screenshot)
        btn_layout.addWidget(self.save_btn)

        # 取消按钮
        self.cancel_btn = QPushButton("✗ 取消")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(btn_layout)
        self.toolbar.setLayout(main_layout)

        # 调整工具栏大小和位置
        self.toolbar.adjustSize()
        toolbar_width = self.toolbar.width()
        toolbar_height = self.toolbar.height()

        # 放置在屏幕底部中央
        x = (screen.width() - toolbar_width) // 2
        y = screen.height() - toolbar_height - 30
        self.toolbar.move(x, y)
        self.toolbar.raise_()

    def paintEvent(self, event):
        """绘制画布"""
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.canvas)

        # 如果正在绘制临时箭头，显示预览
        if self.temp_arrow_drawing and self.draw_mode == "arrow":
            pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            self.draw_arrow(painter, self.arrow_start, self.arrow_end)

    def mousePressEvent(self, event):
        """鼠标/触摸按下事件"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击在工具栏区域
            if self.toolbar.geometry().contains(event.pos()):
                return

            if self.draw_mode == "line":
                self.drawing = True
                self.last_point = event.pos()
            elif self.draw_mode == "arrow":
                self.temp_arrow_drawing = True
                self.arrow_start = event.pos()
                self.arrow_end = event.pos()

    def mouseMoveEvent(self, event):
        """鼠标/触摸移动事件 - 绘制画笔"""
        if event.buttons() & Qt.LeftButton:
            # 检查是否在工具栏区域
            if self.toolbar.geometry().contains(event.pos()):
                return

            if self.draw_mode == "line" and self.drawing:
                painter = QPainter(self.canvas)
                pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                painter.drawLine(self.last_point, event.pos())
                self.last_point = event.pos()
                self.update()
            elif self.draw_mode == "arrow" and self.temp_arrow_drawing:
                self.arrow_end = event.pos()
                self.update()

    def mouseReleaseEvent(self, event):
        """鼠标/触摸释放事件"""
        if event.button() == Qt.LeftButton:
            if self.draw_mode == "line":
                self.drawing = False
            elif self.draw_mode == "arrow" and self.temp_arrow_drawing:
                # 将箭头绘制到画布上
                painter = QPainter(self.canvas)
                pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                self.draw_arrow(painter, self.arrow_start, self.arrow_end)
                painter.end()
                self.temp_arrow_drawing = False
                self.update()

    def draw_arrow(self, painter, start, end):
        """绘制箭头"""
        import math

        # 绘制箭头主线
        painter.drawLine(start, end)

        # 计算箭头方向
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.sqrt(dx * dx + dy * dy)

        if length < 10:  # 太短不绘制箭头头部
            return

        # 归一化方向向量
        dx = dx / length
        dy = dy / length

        # 箭头头部大小
        arrow_size = min(30, length / 3)
        arrow_angle = 0.4  # 箭头角度（弧度）

        # 计算箭头两个翼的端点
        # 左翼
        left_x = end.x() - arrow_size * (dx * math.cos(arrow_angle) + dy * math.sin(arrow_angle))
        left_y = end.y() - arrow_size * (dy * math.cos(arrow_angle) - dx * math.sin(arrow_angle))

        # 右翼
        right_x = end.x() - arrow_size * (dx * math.cos(arrow_angle) - dy * math.sin(arrow_angle))
        right_y = end.y() - arrow_size * (dy * math.cos(arrow_angle) + dx * math.sin(arrow_angle))

        # 绘制箭头头部
        painter.drawLine(end, QPoint(int(left_x), int(left_y)))
        painter.drawLine(end, QPoint(int(right_x), int(right_y)))

    def set_line_mode(self):
        """设置为画线模式"""
        self.draw_mode = "line"
        self.hint_label.setText("✏️ 手指拖动画红线标注 | 按住此框可移动")
        # 更新按钮样式
        self.line_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                min-width: 150px;
                min-height: 60px;
            }
        """)
        self.arrow_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                min-width: 150px;
                min-height: 60px;
            }
        """)

    def set_arrow_mode(self):
        """设置为画箭头模式"""
        self.draw_mode = "arrow"
        self.hint_label.setText("➡️ 拖动画箭头标注 | 按住此框可移动")
        # 更新按钮样式
        self.arrow_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                min-width: 150px;
                min-height: 60px;
            }
        """)
        self.line_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                min-width: 150px;
                min-height: 60px;
            }
        """)

    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Escape:
            # ESC 取消
            self.close()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Enter 保存
            self.save_screenshot()

    def save_screenshot(self):
        """保存截图到 OneDrive 图片文件夹"""
        from datetime import datetime
        import os

        # 保存路径：用户家目录\OneDrive\图片\Screenshots
        screenshots_dir = os.path.join(os.path.expanduser("~"), "OneDrive", "图片", "Screenshots")

        # 如果目录不存在，创建它
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(screenshots_dir, filename)

        self.canvas.save(filepath, "PNG")
        print(f"截图已保存到: {filepath}")

        # 显示保存成功提示
        self.show_save_notification(filepath)
        self.close()

    def show_save_notification(self, filepath):
        """显示保存成功通知"""
        # 创建临时提示窗口
        notification = QLabel(f"✓ 已保存到:\n{filepath}", self)
        notification.setStyleSheet("""
            background-color: rgba(76, 175, 80, 230);
            color: white;
            padding: 20px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
        """)
        notification.adjustSize()

        # 居中显示
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - notification.width()) // 2
        y = (screen.height() - notification.height()) // 2
        notification.move(x, y)
        notification.show()
        notification.raise_()

        # 1.5秒后自动隐藏
        QTimer.singleShot(1500, notification.hide)

    def closeEvent(self, event):
        """关闭事件"""
        self.closed.emit()
        super().closeEvent(event)


class RegionSelector(QWidget):
    """区域选择窗口"""
    region_selected = pyqtSignal(QRect)

    def __init__(self, screen_pixmap):
        super().__init__()
        self.screen_pixmap = screen_pixmap
        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False

        self.setWindowTitle("选择截图区域")
        self.setWindowState(Qt.WindowFullScreen)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setCursor(Qt.CrossCursor)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # 获取屏幕尺寸
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # 创建可拖动的提示标签
        self.hint_label = DraggableLabel("用手指或触控笔拖动选择截图区域 | 按住此框可移动", self)
        self.hint_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 15px;
            border: 2px dashed rgba(150, 150, 150, 100);
        """)
        self.hint_label.adjustSize()
        self.hint_label.move(10, 10)
        self.hint_label.setCursor(Qt.OpenHandCursor)

        # 创建取消按钮
        self.cancel_btn = QPushButton("✗ 取消", self)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                min-width: 150px;
                min-height: 60px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c1170a;
            }
        """)
        self.cancel_btn.clicked.connect(self.close)
        self.cancel_btn.adjustSize()
        # 放在右上角
        self.cancel_btn.move(screen.width() - self.cancel_btn.width() - 20, 20)

    def paintEvent(self, event):
        """绘制半透明遮罩和选择区域"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制原始屏幕截图
        painter.drawPixmap(0, 0, self.screen_pixmap)

        # 创建半透明遮罩层
        mask = QColor(0, 0, 0, 120)

        if self.is_selecting and self.begin != self.end:
            # 获取选择区域
            select_rect = QRect(self.begin, self.end).normalized()

            # 绘制四个遮罩区域（选择区域外的部分）
            # 上方
            painter.fillRect(0, 0, self.width(), select_rect.top(), mask)
            # 下方
            painter.fillRect(0, select_rect.bottom(), self.width(),
                           self.height() - select_rect.bottom(), mask)
            # 左方
            painter.fillRect(0, select_rect.top(), select_rect.left(),
                           select_rect.height(), mask)
            # 右方
            painter.fillRect(select_rect.right(), select_rect.top(),
                           self.width() - select_rect.right(), select_rect.height(), mask)

            # 绘制选择框边框
            pen = QPen(QColor(0, 255, 255), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(select_rect)

            # 绘制四个角的标记
            corner_size = 6
            painter.setBrush(QColor(0, 255, 255))
            # 左上
            painter.drawRect(select_rect.left() - 1, select_rect.top() - 1, corner_size, corner_size)
            # 右上
            painter.drawRect(select_rect.right() - corner_size + 1, select_rect.top() - 1, corner_size, corner_size)
            # 左下
            painter.drawRect(select_rect.left() - 1, select_rect.bottom() - corner_size + 1, corner_size, corner_size)
            # 右下
            painter.drawRect(select_rect.right() - corner_size + 1, select_rect.bottom() - corner_size + 1, corner_size, corner_size)

            # 显示尺寸信息
            size_text = f"{select_rect.width()} x {select_rect.height()}"
            font = painter.font()
            font.setPointSize(12)
            painter.setFont(font)

            # 计算文字位置（显示在选择框右下角外侧）
            text_rect = painter.fontMetrics().boundingRect(size_text)
            text_x = select_rect.right() - text_rect.width() - 5
            text_y = select_rect.bottom() + text_rect.height() + 5

            # 如果超出屏幕，调整位置
            if text_y + text_rect.height() > self.height():
                text_y = select_rect.bottom() - 5
            if text_x < 0:
                text_x = select_rect.left() + 5

            # 绘制文字背景
            painter.fillRect(text_x - 3, text_y - text_rect.height() - 3,
                           text_rect.width() + 6, text_rect.height() + 6,
                           QColor(0, 0, 0, 150))

            # 绘制文字
            painter.setPen(Qt.white)
            painter.drawText(text_x, text_y, size_text)
        else:
            # 没有选择时，全屏遮罩
            painter.fillRect(self.rect(), mask)

    def mousePressEvent(self, event):
        """鼠标/触摸按下 - 开始选择"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击在取消按钮区域
            if self.cancel_btn.geometry().contains(event.pos()):
                return
            self.begin = event.pos()
            self.end = event.pos()
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        """鼠标/触摸移动 - 更新选择区域"""
        if self.is_selecting:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """鼠标/触摸释放 - 完成选择"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            rect = QRect(self.begin, self.end).normalized()

            # 区域太小则取消
            if rect.width() < 10 or rect.height() < 10:
                self.close()
                return

            self.region_selected.emit(rect)
            self.close()

    def keyPressEvent(self, event):
        """ESC取消选择"""
        if event.key() == Qt.Key_Escape:
            self.close()


class FloatingWindow(QWidget):
    """悬浮窗界面"""

    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("截图工具")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # 设置窗口样式 - 优化触屏操作
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 15px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 20px;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                min-width: 200px;
                min-height: 70px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#closeBtn {
                background-color: rgba(244, 67, 54, 200);
                min-width: 45px;
                min-height: 45px;
                max-width: 45px;
                max-height: 45px;
                padding: 0px;
                border-radius: 22px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton#closeBtn:hover {
                background-color: #f44336;
            }
            QPushButton#closeBtn:pressed {
                background-color: #da190b;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """)

        # 布局
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # 标题
        title = QLabel("📸 截图工具")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # 全屏截图按钮
        btn_fullscreen = QPushButton("📷 全屏截图")
        btn_fullscreen.clicked.connect(self.fullscreen_screenshot)
        layout.addWidget(btn_fullscreen)

        # 区域截图按钮
        btn_region = QPushButton("✂️ 区域截图")
        btn_region.clicked.connect(self.region_screenshot)
        layout.addWidget(btn_region)

        # 提示标签
        hint = QLabel("支持触屏画笔标注")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("font-size: 13px; color: #aaa;")
        layout.addWidget(hint)

        self.setLayout(layout)
        self.adjustSize()

        # 创建右上角关闭按钮（隐藏到托盘）
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.clicked.connect(self.hide)
        self.close_btn.setToolTip("隐藏到托盘")
        # 放置在右上角
        self.close_btn.move(self.width() - 50, 5)
        self.close_btn.raise_()

        # 移动到屏幕中心
        self.move_to_center()

    def move_to_center(self):
        """移动窗口到屏幕中心"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def fullscreen_screenshot(self):
        """全屏截图"""
        self.hide()
        # 使用定时器延迟截图，确保窗口完全隐藏
        QTimer.singleShot(100, self._do_fullscreen_screenshot)

    def _do_fullscreen_screenshot(self):
        """执行全屏截图"""
        screen = QApplication.primaryScreen()
        pixmap = screen.grabWindow(0)
        self.parent_app.show_editor(pixmap)

    def region_screenshot(self):
        """区域截图"""
        self.hide()
        # 使用定时器延迟截图，确保窗口完全隐藏
        QTimer.singleShot(100, self._do_region_screenshot)

    def _do_region_screenshot(self):
        """执行区域截图"""
        screen = QApplication.primaryScreen()
        screen_pixmap = screen.grabWindow(0)
        self.parent_app.show_region_selector(screen_pixmap)

    def mousePressEvent(self, event):
        """鼠标/触摸按下 - 用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击在关闭按钮上
            if self.close_btn.geometry().contains(event.pos()):
                return
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        """鼠标/触摸移动 - 拖动窗口"""
        if event.buttons() == Qt.LeftButton:
            # 检查是否在关闭按钮上
            if self.close_btn.geometry().contains(event.pos()):
                return
            self.move(event.globalPos() - self.drag_position)


class ScreenshotApp(QApplication):
    """主应用程序"""

    def __init__(self, argv):
        super().__init__(argv)
        self.floating_window = None
        self.editor_window = None
        self.region_selector = None
        self.init_tray()

    def init_tray(self):
        """初始化系统托盘"""
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)

        # 创建一个简单的图标
        icon = self.create_icon()
        self.tray_icon.setIcon(QIcon(icon))

        # 创建菜单
        tray_menu = QMenu()

        show_action = tray_menu.addAction("显示截图工具")
        show_action.triggered.connect(self.show_floating_window)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self.quit_app)

        self.tray_icon.setContextMenu(tray_menu)

        # 双击事件
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # 显示托盘图标
        self.tray_icon.show()
        self.tray_icon.showMessage(
            "截图工具",
            "程序已启动，双击托盘图标打开截图工具",
            QSystemTrayIcon.Information,
            2000
        )

    def create_icon(self):
        """创建托盘图标"""
        # 创建一个简单的相机图标
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制相机外框
        painter.setBrush(QColor(70, 175, 80))
        painter.setPen(QPen(QColor(50, 150, 60), 2))
        painter.drawRoundedRect(8, 16, 48, 36, 4, 4)

        # 绘制镜头
        painter.setBrush(QColor(200, 200, 200))
        painter.drawEllipse(22, 24, 20, 20)

        # 绘制快门按钮
        painter.setBrush(QColor(255, 100, 100))
        painter.drawRect(44, 12, 8, 6)

        painter.end()

        return pixmap

    def tray_icon_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_floating_window()

    def show_floating_window(self):
        """显示悬浮窗"""
        if self.floating_window is None:
            self.floating_window = FloatingWindow(self)

        self.floating_window.show()
        self.floating_window.raise_()
        self.floating_window.activateWindow()

    def show_editor(self, pixmap):
        """显示编辑窗口"""
        if self.editor_window:
            self.editor_window.close()

        self.editor_window = ScreenshotEditor(pixmap)
        self.editor_window.closed.connect(self.on_editor_closed)
        self.editor_window.show()

    def show_region_selector(self, screen_pixmap):
        """显示区域选择器"""
        self.region_selector = RegionSelector(screen_pixmap)
        self.region_selector.region_selected.connect(self.on_region_selected)
        self.region_selector.show()

    def on_region_selected(self, rect):
        """区域选择完成"""
        # 从屏幕截取选中区域
        screen = QApplication.primaryScreen()
        pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())

        # 显示编辑窗口
        self.show_editor(pixmap)

    def on_editor_closed(self):
        """编辑窗口关闭后，重新显示悬浮窗"""
        if self.floating_window:
            self.floating_window.show()

    def quit_app(self):
        """退出程序"""
        self.tray_icon.hide()
        self.quit()


def main():
    app = ScreenshotApp(sys.argv)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
