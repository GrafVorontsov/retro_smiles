import json
import os

SMILES_DIR = 'smiles'
CONFIG_FILE = 'config.json'
# Твой путь к GitHub
GITHUB_BASE = "https://raw.githubusercontent.com/GrafVorontsov/retro_smiles/main/smiles/"

class SmileModel:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        # Загружаем старый конфиг только для того, чтобы вытянуть URL
        old_urls = {}
        if os.path.exists('config.json'):
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    for tab in cfg:
                        if tab != "_colors":
                            for item in cfg[tab]:
                                # Привязываем URL к имени файла
                                old_urls[os.path.basename(item['file'])] = item.get('url', "")
            except: pass

        # ПОЛНАЯ ОЧИСТКА ПЕРЕД СКАНЕРОМ
        self.data = {"_colors": old_config.get("_colors", {})} if 'old_config' in locals() else {"_colors": {}}
        
        if not os.path.exists(SMILES_DIR): os.makedirs(SMILES_DIR)

        for folder in sorted(os.listdir(SMILES_DIR)):
            folder_path = os.path.join(SMILES_DIR, folder)
            if os.path.isdir(folder_path):
                self.data[folder] = []
                # Сет для проверки дубликатов в этой конкретной папке
                seen_files = set() 
                
                for fname in sorted(os.listdir(folder_path)):
                    if fname.lower().endswith(('.png', '.gif', '.jpg', '.jpeg')) and fname not in seen_files:
                        rel_path = f"{folder}/{fname}"
                        url = old_urls.get(fname, "")
                        
                        self.data[folder].append({"file": rel_path, "url": url})
                        seen_files.add(fname)
        
        self.save_data()
        return self.data

    def save_data(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def load_data_from_folders(self):
        """Сканирует папку smiles и строит структуру вкладок"""
        if not os.path.exists(SMILES_DIR):
            os.makedirs(SMILES_DIR)
            
        new_data = {}
        # Проходим по всем подпапкам в smiles
        for folder_name in sorted(os.listdir(SMILES_DIR)):
            folder_path = os.path.join(SMILES_DIR, folder_name)
            
            if os.path.isdir(folder_path):
                new_data[folder_name] = []
                # Сканируем картинки внутри папки
                for file_name in sorted(os.listdir(folder_path)):
                    if file_name.lower().endswith(('.png', '.gif', '.jpg', '.jpeg')):
                        # Ссылку (URL) берем из старого конфига, если она там есть
                        old_url = self.find_url_in_old_config(folder_name, file_name)
                        new_data[folder_name].append({
                            "file": f"{folder_name}/{file_name}", 
                            "url": old_url
                        })
        
        self.data = new_data
        # Сохраняем обновленный конфиг (уже со структурой папок)
        self.save_data()
    
    def move_smile_physical(self, from_tab, to_tab, index):
        import shutil
        try:
            # 1. Получаем данные о смайле
            smile_data = self.data[from_tab][index]
            old_rel_path = smile_data['file'] # например "Category1/smile.gif"
            file_name = os.path.basename(old_rel_path)
            
            # 2. Формируем пути
            old_full_path = os.path.join(SMILES_DIR, old_rel_path)
            new_rel_path = os.path.join(to_tab, file_name)
            new_full_path = os.path.join(SMILES_DIR, new_rel_path)
            
            # 3. Физически перемещаем файл
            # Создаем папку назначения, если её вдруг нет
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
            shutil.move(old_full_path, new_full_path)
            
            # 4. Обновляем данные в памяти
            smile_data['file'] = new_rel_path
            self.data[to_tab].append(self.data[from_tab].pop(index))
            
            # 5. Сохраняем конфиг
            self.save_data()
            return True
        except Exception as e:
            print(f"Ошибка при перемещении файла: {e}")
            return False

    def set_tab_color(self, tab_name, color):
        if "_colors" not in self.data:
            self.data["_colors"] = {}
        self.data["_colors"][tab_name] = color
        self.save_data()

    def get_tab_color(self, tab_name, default_color):
        # Проверяем, существует ли секция цветов и есть ли там цвет для этой вкладки
        if "_colors" in self.data and tab_name in self.data["_colors"]:
            return self.data["_colors"][tab_name]
        return default_color

    def add_tab(self, name):
        if name not in self.data:
            self.data[name] = []
            return True
        return False

    def reorder_tabs(self, new_names):
        # Создаем новый временный словарь
        new_data = {}
        
        # 1. Сначала переносим вкладки в новом порядке
        for name in new_names:
            if name in self.data:
                new_data[name] = self.data[name]
        
        # 2. Добавляем служебные ключи (например, _colors), если они были
        for key in self.data:
            if key not in new_data:
                new_data[key] = self.data[key]
        
        # Обновляем основные данные и сохраняем файл
        self.data = new_data
        self.save_data()

    def add_smile(self, tab_name, file_name, url=""):
        if tab_name in self.data:
            final_url = url if url else (GITHUB_BASE + file_name)
            self.data[tab_name].append({"file": file_name, "url": final_url})
            self.save_data()

    def move_smile(self, from_tab, to_tab, smile_index):
        if from_tab in self.data and to_tab in self.data:
            smile = self.data[from_tab].pop(smile_index)
            self.data[to_tab].append(smile)
            self.save_data()

    def delete_smile(self, tab_name, index):
        if tab_name in self.data:
            # Вместо простого удаления из списка, мы можем либо удалять физически,
            # либо помечать, если планируешь синхронизацию.
            # Но для твоей задачи — просто удаляем запись из конфига:
            smile_data = self.data[tab_name].pop(index)
            
            # Если хочешь совсем почистить место:
            file_path = os.path.join('smiles', smile_data['file'])
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except: pass
                
            self.save_data()

    def rename_tab(self, old_name, new_name):
        if old_name == new_name: 
            return True # Имя то же самое, просто выходим
            
        old_path = os.path.join(SMILES_DIR, old_name)
        new_path = os.path.join(SMILES_DIR, new_name)

        try:
            if os.path.exists(old_path):
                # 1. Переименовываем папку
                os.rename(old_path, new_path)
                
                # 2. Переносим данные в словаре
                if old_name in self.data:
                    self.data[new_name] = self.data.pop(old_name)
                    # Исправляем пути файлов
                    for sm in self.data[new_name]:
                        sm['file'] = sm['file'].replace(f"{old_name}/", f"{new_name}/")
                
                # 3. Переносим цвет (БЕЗОПАСНО через .pop)
                if "_colors" in self.data:
                    color = self.data["_colors"].pop(old_name, None)
                    if color:
                        self.data["_colors"][new_name] = color
                
                self.save_data()
                return True
        except Exception as e:
            print(f"Ошибка переименования папки: {e}")
            
        return False
            
    def delete_tab(self, name):
        if name in self.data:
            del self.data[name]
            if name in self.data.get("_colors", {}):
                del self.data["_colors"][name]
            self.save_data()