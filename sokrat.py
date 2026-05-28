import json
import time
import hashlib
import string


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


class ShortLinkService:
    def __init__(self, limit=5, base_url="https://TrustMeBro.ly/"):
        self.storage = LinkStorage(limit)
        self.base_url = base_url
        self.id_counter = 0

    def finish(self):
        self.storage.clear_file()
    
    def _generate_short(self, url):
        # Алгоритм генерации уникального кода
        self.id_counter += 1
        raw_string = url + str(time.time()) + str(self.id_counter)
        # Хешируем
        hash_bytes = hashlib.sha256(raw_string.encode()).hexdigest()
        # Конвертируем кусочек хеша в число
        num = int(hash_bytes[:12], 16)
        # Конвертируем число в буквы/цифры 
        return self._base62_encode(num)[:6]
    
    def _base62_encode(self, num):
        chars = string.digits + string.ascii_lowercase + string.ascii_uppercase
        if num == 0:
            return chars[0]
        arr = []
        while num:
            num, rem = divmod(num, 62)
            arr.append(chars[rem])
        return ''.join(reversed(arr))

    def _validate_url(self, raw_url):
        cleaned = raw_url.strip()
        if not cleaned:
            return False, "Ошибка: ссылка не может быть пустой."
        
        return True, cleaned
    
    def _validate_short(self, raw_short):
        cleaned = raw_short.strip()
        
        if not cleaned:
            return False, "Ошибка: код не может быть пустым."
        
        return True, cleaned

    def list_all(self):        
        all_links = self.storage.get_all_links()
        
        if not all_links:
            return "Хранилище пусто. Сократите хотя бы одну ссылку!"
        
        # Сортируем: сначала новые 
        sorted_links = sorted(all_links, key=lambda x: x.created_at, reverse=True)
        
        result_lines = []
        result_lines.append("=" * 60)
        result_lines.append(f"{'КОРОТКАЯ ССЫЛКА':<25} {'ПЕРЕХОДЫ':<10} ОРИГИНАЛЬНАЯ ССЫЛКА")
        result_lines.append("-" * 60)
        
        for link in sorted_links:
            short_full = self.base_url + link.short_url
            # Обрезаем оригинальную ссылку, если она слишком длинная
            original_display = link.original_url
            if len(original_display) > 35:
                original_display = original_display[:32] + "..."
            
            result_lines.append(
                f"{short_full:<25} {link.access_count:<10} {original_display}"
            )
        
        result_lines.append("=" * 60)
        result_lines.append(f"Всего ссылок: {len(all_links)}")
        
        return "\n".join(result_lines)
    
    def shorten(self, long_url):
        is_valid, result = self._validate_url(long_url)
        if not is_valid:
            return result  # Возвращаем сообщение об ошибке
        long_url = result  # Берем очищенную строку
        # Проверяем существование
        existing = self.storage.find_by_original(long_url)
        if existing:
            return self.base_url + existing.short_url
        
        # Генерируем новый
        short = self._generate_short(long_url)
        record = LinkRecord(long_url, short)
        self.storage.add(record)
        return self.base_url + short
    
    def get_original(self, short_url):
        # Убираем base_url, если вставили целую ссылку
        if short_url.startswith(self.base_url):
            short_url = short_url[len(self.base_url):]
        
        is_valid, result = self._validate_short(short_url)
        if not is_valid:
            return result  # Возвращаем сообщение об ошибке
        short_url = result  # Берем очищенную строку
        # Убираем base_url если вставили целую ссылку
        if short_url.startswith(self.base_url):
            short_url = short_url[len(self.base_url):]
        
        record = self.storage.find_by_short(short_url)
        if record:
            self.storage.increment_counter(short_url)
            return record.original_url
        return None
    
    def get_stats(self, short_url):
        if short_url.startswith(self.base_url):
            short_url = short_url[len(self.base_url):]
        record = self.storage.find_by_short(short_url)
        if record:
            return {
                "original": record.original_url,
                "clicks": record.access_count
            }
        return "Ссылка не найдена."

# типо main
if __name__ == "__main__":
    service = ShortLinkService(limit=5) # Лимит в 5 ссылок для теста
    
    while True:
        print()
        print("1. Сократить ссылку")
        print("2. Найти оригинал")
        print("3. Статистика")
        print("4. Вывести список")
        print("5. Выход")
        choice = input("> ")
        
        if choice == '1':
            url = input("Введи URL: ")
            print("Результат:", service.shorten(url))
        elif choice == '2':
            short = input("Введи код: ")
            res = service.get_original(short)
            print("Оригинал:", res if res else "Не найдено")
        elif choice == '3':
            short = input("Введи код: ")
            print(service.get_stats(short))
        elif choice == '4':
            print("\n" + service.list_all())
        elif choice == '5':
            print("Выход из программы.")
            break
        else:
            print("Неизвестная команда. Попробуй снова.")
    service.finish()
