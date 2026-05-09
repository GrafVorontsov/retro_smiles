import os

# Подавляем GTK сообщения в консоли (включая ошибку модуля canberra)
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.xcb.xcb_error=false"
# Если запускаешь в Linux, это перенаправит ошибки GTK в пустоту
if os.name == 'posix':
    os.environ["GTK_MODULES"] = ""
import sys
import logging
# Это заставит Qt помалкивать про мелкие ошибки картинок
os.environ["QT_LOGGING_RULES"] = "qt.gui.imageio=false"
import subprocess
import shutil
import urllib.request
import time
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QPushButton, QScrollArea, QTabWidget, 
                             QMessageBox, QToolButton, QInputDialog, QTabBar, QLineEdit, QLabel,
                             QFrame, QFileDialog, QMenu, QColorDialog, QDialog) # Добавь QMenu и QDialog сюда
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPalette, QColor, QPixmap # Добавь QIcon и QPixmap сюда
from widgets import SmileButton
from models import SmileModel

SMILES_DIR = 'smiles'
ICON_FILE = 'icon.png'

class ColorPicker(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбери цвет")
        self.selected_color = None
        layout = QGridLayout(self)
        
        # Набор из 20 сочных цветов
        colors = [
            "#e74c3c", "#c0392b", "#e67e22", "#d35400", "#f1c40f", 
            "#f39c12", "#2ecc71", "#27ae60", "#1abc9c", "#16a085",
            "#3498db", "#2980b9", "#9b59b6", "#8e44ad", "#34495e", 
            "#2c3e50", "#7f8c8d", "#95a5a6", "#bdc3c7", "#ecf0f1"
        ]
        
        for i, color in enumerate(colors):
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(f"background-color: {color}; border: 1px solid #555; border-radius: 4px;")
            btn.clicked.connect(lambda ch, c=color: self.choose(c))
            layout.addWidget(btn, i // 5, i % 5)

    def choose(self, color):
        self.selected_color = color
        self.accept()

class DropTabBar(QTabBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.parent_app = parent

    def dragEnterEvent(self, event):
        if event.mimeData().hasText(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        index = self.tabAt(event.position().toPoint())
        if index != -1:
            self.setCurrentIndex(index)
            event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            data = event.mimeData().text()
            from_tab, smile_index = data.split('|')
            
            # Куда бросили
            to_tab_index = self.tabAt(event.position().toPoint())
            if to_tab_index == -1: return
            to_tab = self.tabText(to_tab_index)
            
            # Если бросили в ту же вкладку — ничего не делаем
            if from_tab == to_tab: return

            # Переносим
            if self.parent_app.model.move_smile_physical(from_tab, to_tab, int(smile_index)):
                # Обновляем интерфейс
                self.parent_app.render_tabs()
                # Остаемся на текущей вкладке или переключаемся (как тебе удобнее)
                # Если хочешь видеть результат сразу — раскомментируй строку ниже:
                # self.parent_app.tabs.setCurrentIndex(to_tab_index)
                event.acceptProposedAction()

class TabEditDialog(QDialog):
    def __init__(self, parent=None, title="Категория", name="", color="#4a90e2"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.selected_color = color
        self.result_name = name
        
        layout = QVBoxLayout(self)
        
        # Поле ввода имени
        layout.addWidget(QLabel("Название категории:"))
        self.name_input = QLineEdit(name)
        self.name_input.setStyleSheet("padding: 5px; font-size: 14px;")
        layout.addWidget(self.name_input)
        
        # Сетка цветов
        layout.addWidget(QLabel("Выберите цвет вкладки:"))
        grid = QGridLayout()
        colors = [
            "#e74c3c", "#c0392b", "#e67e22", "#d35400", "#f1c40f", 
            "#f39c12", "#2ecc71", "#27ae60", "#1abc9c", "#16a085",
            "#3498db", "#2980b9", "#9b59b6", "#8e44ad", "#34495e", 
            "#2c3e50", "#7f8c8d", "#95a5a6", "#bdc3c7", "#ecf0f1"
        ]
        
        self.buttons = []
        for i, c in enumerate(colors):
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setCheckable(True)
            btn.setStyleSheet(f"background-color: {c}; border: 2px solid #555; border-radius: 4px;")
            btn.clicked.connect(lambda ch, col=c: self.set_color(col))
            if c == color: 
                btn.setChecked(True)
                btn.setStyleSheet(f"background-color: {c}; border: 2px solid white; border-radius: 4px;")
            grid.addWidget(btn, i // 5, i % 5)
            self.buttons.append((btn, c))
            
        layout.addLayout(grid)
        
        # Кнопки ОК/Отмена
        btns_layout = QHBoxLayout()
        ok_btn = QPushButton("Сохранить")
        ok_btn.clicked.connect(self.accept_data)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btns_layout.addWidget(ok_btn)
        btns_layout.addWidget(cancel_btn)
        layout.addLayout(btns_layout)

    def set_color(self, color):
        self.selected_color = color
        for btn, c in self.buttons:
            if c == color:
                btn.setStyleSheet(f"background-color: {c}; border: 2px solid white; border-radius: 4px;")
            else:
                btn.setStyleSheet(f"background-color: {c}; border: 2px solid #555; border-radius: 4px;")

    def accept_data(self):
        self.result_name = self.name_input.text().strip()
        if self.result_name:
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Введите название!")

class RetroSmiles(QWidget):
    def __init__(self):
        super().__init__()
        if not os.path.exists(SMILES_DIR): 
            os.makedirs(SMILES_DIR)
        
        # Если папка пуста — предлагаем загрузку
        if not os.listdir(SMILES_DIR):
            self.first_run_dialog()
            
        self.model = SmileModel()
        self.initUI()

    def first_run_dialog(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Первый запуск")
        msg.setText("Папка смайлов пуста. Как поступим?")
        
        git_btn = msg.addButton("🌐 Скачать с GitHub", QMessageBox.ButtonRole.ActionRole)
        backup_btn = msg.addButton("📁 Загрузить бэкап", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton("❌ Начать с нуля", QMessageBox.ButtonRole.RejectRole)
        
        msg.exec()
        
        if msg.clickedButton() == git_btn:
            self.sync_from_github()
        elif msg.clickedButton() == backup_btn:
            self.restore_from_backup()

    def sync_from_github(self):
        # Тут вставь свою ссылку на репозиторий
        repo_url = "https://github.com/GrafVorontsov/retro_smiles.git"
        try:
            # Используем git clone прямо в папку smiles
            # Нужен установленный git в системе!
            subprocess.run(['git', 'clone', repo_url, SMILES_DIR + "_temp"], check=True)
            # Переносим всё из временной папки в smiles
            for item in os.listdir(SMILES_DIR + "_temp"):
                s = os.path.join(SMILES_DIR + "_temp", item)
                d = os.path.join(SMILES_DIR, item)
                if os.path.isdir(s): shutil.copytree(s, d, dirs_exist_ok=True)
                else: shutil.copy2(s, d)
            shutil.rmtree(SMILES_DIR + "_temp")
            QMessageBox.information(self, "Успех", "База успешно синхронизирована!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось клонировать репо: {e}")

    def initUI(self):
        self.setWindowTitle('Retro Smiles')
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.tabs = QTabWidget()
        self.tabs.setTabBar(DropTabBar(self)) # Это у тебя уже есть для переноса смайлов
        
        # --- ВОТ ЭТИ ДВЕ СТРОКИ ВКЛЮЧАЮТ ПЕРЕТАСКИВАНИЕ ---
        self.tabs.setMovable(True) 
        self.tabs.tabBar().setMovable(True) 
        
        # Подключаем сохранение порядка
        self.tabs.tabBar().tabMoved.connect(self.save_new_tabs_order)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.remove_tab)

        # ФИКС ТУЛТИПОВ (чтобы не были белыми полосками)
        self.setStyleSheet("""
            QToolTip { 
                background-color: #333333; 
                color: white; 
                border: 1px solid #555555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        
        # --- КРАСИВАЯ, АККУРАТНАЯ КНОПКА "+" ---
        # Создаем QToolButton, так как она лучше подходит для таких целей
        self.add_tab_btn = QToolButton(self.tabs)
        self.add_tab_btn.setText("+")

        # 1. ЗАДАЕМ КОМПАКТНЫЙ РАЗМЕР И УБИРАЕМ КВАДРАТНОСТЬ
        # Сделаем её чуть меньше и аккуратнее
        self.add_tab_btn.setFixedSize(28, 26) 
        self.add_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_tab_btn.setToolTip("Добавить новую категорию")

        # 2. ПРИМЕНЯЕМ СТИЛИ (CSS/QSS) ДЛЯ ТЕМНОЙ ТЕМЫ
        # Сделаем её плоской, скругленной и центрированной
        self.add_tab_btn.setStyleSheet("""
            QToolButton { 
                border: none;               /* Убираем все рамки */
                border-radius: 4px;         /* Легкое скругление углов */
                background-color: transparent; /* В обычном состоянии прозрачный фон */
                color: #aaaaaa;             /* Неяркий серый цвет плюсика */
                font-weight: bold; 
                font-size: 16px;            /* Чуть побольше сам плюсик */
                
                /* ВАЖНО: Отступы, чтобы кнопка не липла к краям и была по центру */
                margin-right: 8px;          /* Отступ от правого края окна */
                margin-top: 2px;            /* Сдвигаем чуть вниз, чтобы центрировать с вкладками */
                margin-bottom: 2px;         /* Оставляем зазор снизу */
            }
            
            /* Эффект при наведении мыши (как на твоем скриншоте у вкладок) */
            QToolButton:hover { 
                background-color: rgba(255, 255, 255, 0.1); /* Легкая светлая подсветка */
                color: white;                                /* Белый плюсик при наведении */
            }
            
            /* Эффект при нажатии */
            QToolButton:pressed { 
                background-color: rgba(255, 255, 255, 0.2); 
            }
        """)

        self.add_tab_btn.clicked.connect(self.add_tab)
        # Размещаем кнопку в правом верхнем углу панели вкладок
        self.tabs.setCornerWidget(self.add_tab_btn, Qt.Corner.TopRightCorner)
        
        layout.addWidget(self.tabs)

        # Немного приберем рамку самой панели
        self.tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #333333; /* Темная, неброская рамка вокруг контента */
                border-radius: 4px;
                top: -1px; /* Слияние с заголовками вкладок */
            }
        """)

        # --- НИЖНЯЯ ПАНЕЛЬ С КНОПКАМИ ---
        bottom_layout = QHBoxLayout()

        # Кнопка Обновить
        self.refresh_btn = QPushButton("🔄 Обновить базу")
        self.refresh_btn.setFixedHeight(35)
        self.refresh_btn.clicked.connect(self.refresh_all)
        bottom_layout.addWidget(self.refresh_btn)

        # Обновленная кнопка Добавить
        self.add_smile_btn = QPushButton("📥 Добавить смайл по ссылке")
        self.add_smile_btn.setFixedHeight(35)
        self.add_smile_btn.clicked.connect(self.add_smile_by_url)
        bottom_layout.addWidget(self.add_smile_btn)

        layout.addLayout(bottom_layout)

        self.render_tabs()

    def refresh_all(self):
        # 1. Заставляем модель перечитать папки
        self.model.load_data() 
        # 2. Перерисовываем вкладки
        self.render_tabs()
        
        # Показываем уведомление, что всё готово
        if hasattr(self, 'toast'):
            self.toast = ToastNotification("✅ Список смайлов обновлен из папок!")
            self.toast.show_toast()

    def save_new_tabs_order(self, from_idx, to_idx):
        # Собираем текущий порядок имен вкладок
        new_order = []
        for i in range(self.tabs.count()):
            new_order.append(self.tabs.tabText(i))
        
        # Отправляем в модель на сохранение
        self.model.reorder_tabs(new_order)

    def tab_context_menu(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx == -1: return
        
        tab_name = self.tabs.tabText(idx)
        # Получаем текущий цвет, чтобы диалог открылся с ним
        current_color = self.model.get_tab_color(tab_name, "#4a90e2")
        
        menu = QMenu(self)
        edit_act = menu.addAction("✏️ Изменить категорию")
        del_act = menu.addAction("❌ Удалить категорию")
        
        action = menu.exec(self.tabs.tabBar().mapToGlobal(pos))
        
        if action == edit_act:
            dialog = TabEditDialog(self, title="Редактирование", name=tab_name, color=current_color)
            if dialog.exec():
                new_name = dialog.result_name
                new_color = dialog.selected_color
                
                # 1. Если имя изменилось — переименовываем папку и данные
                if new_name != tab_name:
                    if self.model.rename_tab(tab_name, new_name):
                        tab_name = new_name # Дальше работаем уже с новым именем
                
                # 2. Обновляем цвет (даже если имя осталось прежним)
                self.model.set_tab_color(tab_name, new_color)
                
                # 3. Перерисовываем всё
                self.render_tabs()
        
        elif action == del_act:
            self.remove_tab(idx)

    def render_tabs(self):
        # 1. ПОЛНАЯ ОЧИСТКА (без сохранения позиции, раз она бесит)
        self.tabs.blockSignals(True)
        while self.tabs.count() > 0:
            w = self.tabs.widget(0)
            self.tabs.removeTab(0)
            if w: w.deleteLater()

        auto_colors = ["#4a90e2", "#e67e22", "#2ecc71", "#e74c3c", "#9b59b6"]
        real_idx = 0

        for tab_name, smiles in self.model.data.items():
            if tab_name == "_colors": continue
            
            # Создаем скролл-область
            scroll = QScrollArea()
            scroll.setWidgetResizable(True) # Это заставляет контейнер растягиваться
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            # Принудительно включаем скроллбар
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            
            container = QWidget()
            # Важно: задаем контейнеру имя, чтобы он подхватил стили если надо
            container.setObjectName("tabContainer") 
            
            grid = QGridLayout(container)
            grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            grid.setContentsMargins(10, 10, 10, 10)
            grid.setSpacing(8)
            
            # Убираем жесткий MinimumHeight, который сжимал плитки!
            # Вместо него даем сетке самой считать высоту
            grid.setSizeConstraint(QGridLayout.SizeConstraint.SetMinAndMaxSize)

            # Рендерим первые 150
            for i, sm in enumerate(smiles[:150]):
                self.create_smile_btn(grid, tab_name, sm, i)
            
            if len(smiles) > 150:
                QTimer.singleShot(10, lambda t=tab_name, g=grid, s=smiles[150:], offset=150: 
                                  self.load_next_chunk(t, g, s, offset))

            scroll.setWidget(container)
            self.tabs.addTab(scroll, tab_name)

            # Покраска вкладок
            color_hex = self.model.get_tab_color(tab_name, auto_colors[real_idx % len(auto_colors)])
            self.tabs.tabBar().setTabTextColor(real_idx, QColor(color_hex))
            real_idx += 1

        # Восстанавливаем меню вкладок
        self.tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        try: self.tabs.tabBar().customContextMenuRequested.disconnect()
        except: pass
        self.tabs.tabBar().customContextMenuRequested.connect(self.tab_context_menu)

        self.tabs.blockSignals(False)

    def restore_scroll(self, pos):
        widget = self.tabs.currentWidget()
        if isinstance(widget, QScrollArea):
            widget.verticalScrollBar().setValue(pos)

    def load_next_chunk(self, tab_name, grid, remaining_smiles, offset):
        chunk_size = 100
        chunk = remaining_smiles[:chunk_size]
        next_remaining = remaining_smiles[chunk_size:]
        
        for i, sm in enumerate(chunk):
            self.create_smile_btn(grid, tab_name, sm, offset + i)
            
        if next_remaining:
            QTimer.singleShot(5, lambda: self.load_next_chunk(tab_name, grid, next_remaining, offset + chunk_size))
        else:
            # Когда всё догрузилось — убираем фиксированную высоту, чтобы контейнер подстроился точно
            if grid.parentWidget():
                grid.parentWidget().setMinimumHeight(0)

    def lazy_load_tail(self, tab_name, grid, smiles_tail, start_idx):
        for i, sm in enumerate(smiles_tail):
            self.create_smile_btn(grid, tab_name, sm, start_idx + i)

    def create_smile_btn(self, grid, tab_name, sm, index):
        # Теперь sm['file'] — это уже "Название_Вкладки/имя_файла.gif"
        path = os.path.join(SMILES_DIR, sm['file']) 
        
        # Проверка: если файла нет по этому пути, кнопка не создаст пустой квадрат
        if not os.path.exists(path):
            return 

        btn = SmileButton(path, sm['url'], self, index)
        btn.clicked.connect(lambda ch, u=sm['url']: self.copy_url(u))
        grid.addWidget(btn, index // 10, index % 10)

    def copy_url(self, url):
        if not url:
            return
        # Оборачиваем прямую ссылку в теги [img]
        bb_code_url = f"[img]{url}[/img]"
        
        process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
        process.communicate(input=bb_code_url.encode())

    def add_smile_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать смайлы", "", "Images (*.gif *.png *.jpg)")
        if not files: return
        
        current_tab = self.tabs.tabText(self.tabs.currentIndex())
        tab_dir = os.path.join(SMILES_DIR, current_tab)
        os.makedirs(tab_dir, exist_ok=True)

        for f in files:
            name = os.path.basename(f)
            dest = os.path.join(tab_dir, name)
            if not os.path.exists(dest): 
                import shutil
                shutil.copy2(f, dest)
        
        # После копирования просто обновляем всё
        self.refresh_all()

    def add_tab(self):
        dialog = TabEditDialog(self, title="Новая категория")
        if dialog.exec():
            name = dialog.result_name
            color = dialog.selected_color
            
            # Создаем физическую папку
            path = os.path.join(SMILES_DIR, name)
            if not os.path.exists(path):
                os.makedirs(path)
                
            if self.model.add_tab(name): # В модели просто добавляем ключ
                self.model.set_tab_color(name, color)
                self.render_tabs()

    def add_smile_by_url(self):
        url, ok = QInputDialog.getText(self, "Добавить по ссылке", 
                                     "Вставьте прямую ссылку на GIF/PNG:",
                                     QLineEdit.EchoMode.Normal)
        
        if ok and url.strip():
            url = url.strip()
            try:
                # 1. Сразу определяем, куда качать (папка текущей вкладки)
                current_tab = self.tabs.tabText(self.tabs.currentIndex())
                tab_dir = os.path.join(SMILES_DIR, current_tab)
                os.makedirs(tab_dir, exist_ok=True)

                # 2. Имитируем браузер
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                # 3. Вытягиваем расширение и генерируем имя
                ext = url.split('.')[-1].split('?')[0]
                if len(ext) > 4 or len(ext) < 3: ext = "gif"
                
                file_name = f"sync_{int(time.time())}.{ext}"
                # Правильный полный путь к файлу
                full_dest_path = os.path.join(tab_dir, file_name)

                # 4. Качаем напрямую в нужную папку
                with urllib.request.urlopen(req, timeout=10) as response:
                    with open(full_dest_path, 'wb') as out_file:
                        out_file.write(response.read())
                
                # 5. Сообщаем модели (путь теперь относительный папки smiles: "Вкладка/файл.gif")
                rel_path = f"{current_tab}/{file_name}"
                self.model.add_smile(current_tab, rel_path, url)
                
                # 6. Обновляем интерфейс
                self.render_tabs()
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка загрузки", f"Не удалось скачать файл:\n{str(e)}")

    def remove_tab(self, index):
        tab_name = self.tabs.tabText(index)
        smiles_count = len(self.model.data.get(tab_name, []))
        
        # Первое предупреждение
        reply1 = QMessageBox.question(
            self, "Подтверждение", 
            f"Вы уверены, что хотите удалить категорию '{tab_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply1 == QMessageBox.StandardButton.Yes:
            # Второе, более серьезное предупреждение
            reply2 = QMessageBox.warning(
                self, "ВНИМАНИЕ!", 
                f"Это действие безвозвратно удалит вкладку и все смайлы в ней ({smiles_count} шт.).\nПродолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                defaultButton=QMessageBox.StandardButton.No
            )
            
            if reply2 == QMessageBox.StandardButton.Yes:
                self.model.delete_tab(tab_name)
                self.render_tabs()

    def delete_smile(self, btn_obj):
        if QMessageBox.question(self, "Retro Smiles", "Удалить смайл?") == QMessageBox.StandardButton.Yes:
            self.model.delete_smile(self.tabs.tabText(self.tabs.currentIndex()), btn_obj.index)
            self.render_tabs()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Правильный импорт иконки
    from PyQt6.QtGui import QIcon # Дублируем импорт для надежности внутри блока
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, ICON_FILE)
    
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    ex = RetroSmiles()
    ex.show()
    sys.exit(app.exec())