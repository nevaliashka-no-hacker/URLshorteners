import json
import time

class LinkRecord:
    def __init__(self, original, short, created_at=None):
        self.original_url = original
        self.short_url = short
        self.access_count = 0
        self.created_at = created_at if created_at else time.time()
    
    # загрузка в json
    def to_dict(self):
        return {
            "url": self.original_url,
            "short": self.short_url,
            "count": self.access_count,
            "created": self.created_at
        }
    
    # выгрузка из json
    @staticmethod
    def from_dict(data):
        record = LinkRecord(data["url"], data["short"], data["created"])
        record.access_count = data["count"]
        return record
    

# хранилище ссылок и статистики (с json файлом)
class LinkStorage:
    def __init__(self, limit, filename="storage.json"):
        self.limit = limit
        self.filename = filename
        # для хранения записей в памяти
        self.links = [] 
        self.load_from_file()
    
    def load_from_file(self):
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                self.links = [LinkRecord.from_dict(item) for item in data]
        except (FileNotFoundError, json.JSONDecodeError):
            self.links = []
    
    def save_to_file(self):
        data = [link.to_dict() for link in self.links]
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=4)

    def clear_file(self):
        data = []
        self.links = []
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=4)

    def get_all_links(self):
        # копия, чтобы хранилице никак не испортилось, если что случится
        return self.links.copy()
    
    def find_by_original(self, url):
        for link in self.links:
            if link.original_url == url:
                return link
        return None
    
    def find_by_short(self, short):
        for link in self.links:
            if link.short_url == short:
                return link
        return None
    
    def add(self, record):
        # ссылка уже есть?
        existing = self.find_by_original(record.original_url)
        if existing:
            # есть - возвращаем оригинал
            return existing 
            
        # проверка лимита
        while len(self.links) >= self.limit:
            self.evict_oldest_or_least_used()
            
        # + новая ссылка в хранилище
        self.links.append(record)
        self.save_to_file()
        return record
        
    
    def increment_counter(self, short):
        record = self.find_by_short(short)
        if record:
            record.access_count += 1
            self.save_to_file()
    
    def evict_oldest_or_least_used(self):
        if not self.links:
            return
        
        # сортировка: 
        # 1 по счетчику по возрастанию
        # 2 по дате (старше - выше)
        def sort_key(link):
            return (link.access_count, link.created_at)
        
        self.links.sort(key=sort_key)
        removed = self.links.pop(0)
        print(f"(Система: удалена ссылка '{removed.short_url}' с {removed.access_count} переходами)")
