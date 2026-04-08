import urllib.request
import urllib.parse
import json

BASE = "http://localhost:8000"

def post(path, data, token=None):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + path, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# Login
resp = post("/auth/login", {"email": "demo", "password": "demo123"})
token = resp["access_token"]
print(f"Logged in, token: {token[:20]}...")

apartments = [
    {
        "title": "Уютная студия у метро",
        "description": "Светлая студия после ремонта. Новая мебель и техника. 5 минут пешком до метро Проспект Мира. Тихий двор, консьерж.",
        "price": 28000, "address": "ул. Проспект Мира, 45", "city": "Москва",
        "rooms": 0, "area": 32.5, "floor": 7, "total_floors": 16,
        "type": "Rent", "deal_type": "LongTerm",
        "has_furniture": True, "has_parking": False, "pets_allowed": False,
    },
    {
        "title": "2-комнатная квартира на Арбате",
        "description": "Просторная квартира в историческом центре. Высокие потолки, паркет, два балкона. Рядом парк и рестораны.",
        "price": 65000, "address": "Арбат, 12", "city": "Москва",
        "rooms": 2, "area": 68.0, "floor": 3, "total_floors": 5,
        "type": "Rent", "deal_type": "LongTerm",
        "has_furniture": True, "has_parking": False, "pets_allowed": True,
    },
    {
        "title": "3-комн. бизнес-класс с парковкой",
        "description": "Квартира в ЖК бизнес-класса. Закрытая территория, подземная парковка, консьерж 24/7. Рядом школа и детский сад.",
        "price": 95000, "address": "Ленинградский проспект, 80", "city": "Москва",
        "rooms": 3, "area": 92.0, "floor": 12, "total_floors": 25,
        "type": "Rent", "deal_type": "LongTerm",
        "has_furniture": True, "has_parking": True, "pets_allowed": False,
    },
    {
        "title": "Апартаменты на Невском посуточно",
        "description": "Современные апартаменты с панорамными окнами. SmartTV, скоростной Wi-Fi. Идеально для командировок и туристов.",
        "price": 4500, "address": "Невский проспект, 55", "city": "Санкт-Петербург",
        "rooms": 1, "area": 45.0, "floor": 6, "total_floors": 9,
        "type": "Rent", "deal_type": "Daily",
        "has_furniture": True, "has_parking": False, "pets_allowed": False,
    },
    {
        "title": "1-комн. квартира рядом с ВДНХ",
        "description": "Уютная квартира после косметического ремонта. Вся необходимая мебель и техника. Тихий двор, рядом метро ВДНХ.",
        "price": 42000, "address": "Ботаническая ул., 25", "city": "Москва",
        "rooms": 1, "area": 38.0, "floor": 4, "total_floors": 9,
        "type": "Rent", "deal_type": "LongTerm",
        "has_furniture": True, "has_parking": False, "pets_allowed": True,
    },
    {
        "title": "Продажа: 2-комн. в новостройке",
        "description": "Квартира 2023 года постройки. Черновая отделка, свободная планировка. Отличный вариант для инвестиций или собственного жилья.",
        "price": 8500000, "address": "ул. Белобородова, 16", "city": "Москва",
        "rooms": 2, "area": 58.5, "floor": 9, "total_floors": 20,
        "type": "Sale", "deal_type": "LongTerm",
        "has_furniture": False, "has_parking": True, "pets_allowed": False,
    },
    {
        "title": "Краткосрочная аренда у Эрмитажа",
        "description": "Историческая квартира в 5 минутах от Эрмитажа. Высокие лепные потолки, оригинальный паркет. Полностью оборудована.",
        "price": 55000, "address": "Дворцовая наб., 8", "city": "Санкт-Петербург",
        "rooms": 2, "area": 74.0, "floor": 2, "total_floors": 4,
        "type": "Rent", "deal_type": "ShortTerm",
        "has_furniture": True, "has_parking": False, "pets_allowed": False,
    },
    {
        "title": "Студия с видом на море в Сочи",
        "description": "Современная студия с панорамным видом на Чёрное море. Новый дом, закрытая территория, бассейн. Идеально для отдыха.",
        "price": 3800, "address": "ул. Навагинская, 18", "city": "Сочи",
        "rooms": 0, "area": 28.0, "floor": 8, "total_floors": 12,
        "type": "Rent", "deal_type": "Daily",
        "has_furniture": True, "has_parking": True, "pets_allowed": True,
    },
    {
        "title": "4-комн. пентхаус с террасой",
        "description": "Роскошный пентхаус на последнем этаже. Панорамные окна, просторная терраса с барбекю, два санузла. Вид на весь город.",
        "price": 180000, "address": "Садовое кольцо, 5", "city": "Москва",
        "rooms": 4, "area": 150.0, "floor": 20, "total_floors": 20,
        "type": "Rent", "deal_type": "LongTerm",
        "has_furniture": True, "has_parking": True, "pets_allowed": True,
    },
    {
        "title": "Комната в центре Екатеринбурга",
        "description": "Светлая комната в 3-комнатной квартире. Два соседа, чистая кухня и ванная. Рядом университет и остановки.",
        "price": 12000, "address": "ул. Малышева, 33", "city": "Екатеринбург",
        "rooms": 1, "area": 18.0, "floor": 2, "total_floors": 9,
        "type": "Rent", "deal_type": "LongTerm",
        "has_furniture": True, "has_parking": False, "pets_allowed": False,
    },
]

for apt in apartments:
    try:
        r = post("/apartments/", apt, token)
        print(f"  Created: [{r['id']}] {r['title']}")
    except Exception as e:
        print(f"  ERROR {apt['title']}: {e}")

print("Done.")
