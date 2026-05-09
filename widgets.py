import os
import subprocess
from PyQt6.QtWidgets import (QPushButton, QLabel, QFrame, QMenu, QApplication, 
                             QInputDialog, QMessageBox)
from PyQt6.QtGui import QIcon, QPixmap, QAction, QCursor, QDrag, QDesktopServices, QMovie
from PyQt6.QtCore import QSize, Qt, QPoint, QMimeData, QUrl, QTimer, QPropertyAnimation, QEasingCurve

class HoverPreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.WindowTransparentForInput)
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet("background-color: palette(window); border: 2px solid palette(highlight); border-radius: 5px;")
        self.setScaledContents(True)

class ToastNotification(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowTransparentForInput)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            background-color: #333;
            color: white;
            border-radius: 15px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: bold;
            border: 1px solid #555;
        """)
        self.adjustSize()

    def show_toast(self):
        # Позиционируем чуть выше курсора
        pos = QCursor.pos()
        self.move(pos.x() - self.width() // 2, pos.y() - 70)
        self.show()
        # Самоуничтожение через 1.2 сек
        QTimer.singleShot(1200, self.deleteLater)

class SmileButton(QPushButton):
    def __init__(self, file_path, remote_url, parent_app, index):
        super().__init__()
        self.file_path = file_path
        self.remote_url = remote_url
        self.parent_app = parent_app
        self.index = index
        self.setFixedSize(66, 66)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Разрешаем кнопке принимать события мыши правильно
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.setStyleSheet("""
            QPushButton { border: 1px solid palette(mid); border-radius: 8px; background-color: palette(base); }
            QPushButton:hover { border: 2px solid palette(highlight); background-color: palette(button); }
        """)
        
        if os.path.exists(file_path):
            self.setIcon(QIcon(file_path))
            self.setIconSize(QSize(50, 50))

    def enterEvent(self, event):
        self.preview = HoverPreview()
        self.movie = QMovie(self.file_path)
        
        if not self.movie.isValid():
            pix = QPixmap(self.file_path)
            orig_w, orig_h = (pix.width(), pix.height()) if not pix.isNull() else (50, 50)
        else:
            self.movie.jumpToFrame(0)
            size = self.movie.currentImage().size()
            orig_w, orig_h = size.width(), size.height()

        # Масштабирование
        scale_factor = 2.0
        if orig_w < 60 or orig_h < 60:
            scale_factor = 3.0
            
        w, h = int(orig_w * scale_factor), int(orig_h * scale_factor)
        if w < 120: 
            ratio = 120 / w
            w, h = 120, int(h * ratio)

        if w > 300 or h > 300:
            ratio = min(300 / w, 300 / h)
            w, h = int(w * ratio), int(h * ratio)

        self.preview.setFixedSize(w, h)
        
        if self.movie.isValid():
            self.preview.setMovie(self.movie)
            self.movie.setScaledSize(self.preview.size())
            self.movie.start()
        else:
            self.preview.setPixmap(pix)

        cursor_pos = QCursor.pos()
        self.preview.move(cursor_pos.x() - w - 10, cursor_pos.y() - h - 10)
        self.preview.show()

    def leaveEvent(self, event):
        if hasattr(self, 'movie'): self.movie.stop()
        if hasattr(self, 'preview'): self.preview.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event) # ВАЖНО: передаем событие дальше

    def mouseReleaseEvent(self, event):
        # Проверяем, что это был именно клик, а не завершение перетаскивания
        if event.button() == Qt.MouseButton.LeftButton:
            # Если мышь не ушла далеко от места нажатия — это клик
            if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
                if self.remote_url:
                    self.parent_app.copy_url(self.remote_url)
                    # Создаем уведомление
                    self.toast = ToastNotification("✅ Ссылка скопирована")
                    self.toast.show_toast()
                else:
                    QMessageBox.information(self, "Retro Smiles", "Нет ссылки! ПКМ -> Изменить URL")
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton): return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance(): return

        drag = QDrag(self)
        mime_data = QMimeData()
        tab_name = self.parent_app.tabs.tabText(self.parent_app.tabs.currentIndex())
        mime_data.setText(f"{tab_name}|{self.index}")
        drag.setMimeData(mime_data)
        drag.setPixmap(self.grab())
        drag.exec(Qt.DropAction.MoveAction)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        check_link = menu.addAction("🔍 Проверить ссылку")
        edit_url = menu.addAction("🔗 Изменить URL")
        menu.addSeparator()
        delete_sm = menu.addAction("❌ Удалить смайл")
        
        action = menu.exec(event.globalPos())
        if action == check_link:
            if self.remote_url: QDesktopServices.openUrl(QUrl(self.remote_url))
        elif action == edit_url:
            new_url, ok = QInputDialog.getText(self, "URL", "Ссылка:", text=self.remote_url)
            if ok:
                self.remote_url = new_url
                tab_name = self.parent_app.tabs.tabText(self.parent_app.tabs.currentIndex())
                self.parent_app.model.data[tab_name][self.index]['url'] = new_url
                self.parent_app.model.save_data()
        elif action == delete_sm:
            self.parent_app.delete_smile(self)