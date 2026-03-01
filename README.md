# Telegram To-Do бот (SQLite)

Telegram-бот для списка дел: одноразовые и ежедневные задачи, кнопки, статистика. Данные в SQLite. 
## Возможности

- **Одноразовые задачи** — сделал и забыл.
- **Ежедневные задачи** — отмечаешь каждый день заново (например «Пить воду», «Зарядка»).
- **Кнопки** — основное меню и действия под списком (Сделано / Удалить / Обновить).
- **Статистика** — дни с выполнением, текущая и лучшая серия дней подряд, всего отметок.

## Стек

- Python 3
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (async)
- SQLite3 (стандартная библиотека)

## Структура проекта

```
Todo/
├── main.py           # Бот: команды, кнопки, обработчики
├── database.py       # SQLite: задачи, лог выполнений, статистика
├── requirements.txt
├── run.bat           # Запуск одной кнопкой (Windows)
├── .env.example      # Пример файла с токеном (скопируй в .env)
├── .gitignore
└── README.md
```

Файлы `.env`, `token.txt` и `todo.db` в репозиторий не попадают (см. `.gitignore`).

## Установка и запуск

### 1. Клонирование и зависимости

```bash
git clone https://github.com/Alamanss/todo-bot.git
cd todo-bot
pip install -r requirements.txt
```
(Если клонируешь чужой репо — в URL будет другой логин вместо `Alamanss`.)

### 2. Токен бота

1. В Telegram открой [@BotFather](https://t.me/BotFather).
2. Отправь `/newbot`, придумай имя и username бота.
3. Скопируй выданный токен.

### 3. Настройка токена (один из способов)

**Вариант А — файл `.env`**

```bash
cp .env.example .env
```

Открой `.env` и подставь свой токен:

```
BOT_TOKEN=1234567890:ABCdefGHIjkl...
```

**Вариант Б — файл `token.txt`**

Создай в папке проекта файл `token.txt`, в первой строке напиши только токен (без `BOT_TOKEN=`).

**Вариант В — переменная окружения**

- Windows (PowerShell): `$env:BOT_TOKEN = "твой_токен"`
- Linux/macOS: `export BOT_TOKEN="твой_токен"`

### 4. Запуск

- **Windows:** дважды нажми на `run.bat` или в терминале: `py main.py`
- **Linux/macOS:** `python3 main.py`

В консоли должно появиться: `Бот запущен.` После этого открой бота в Telegram и нажми **Start**.

## Использование

- **📋 Мой список** — показать задачи (в работе / сделано), под сообщением кнопки «Сделано» / «Удалить» и «Обновить список».
- **➕ Новая задача** — ввести текст, затем выбрать «Один раз» или «🔄 Каждый день».
- **📊 Статистика** — дни с выполнением, серии дней подряд, всего отметок.

Команды: `/start`, `/add`, `/list`, `/done <номер>`, `/delete <номер>`, `/stats`.

## Для портфолио

В проекте видно:

- Telegram Bot API (команды, Reply- и Inline-клавиатуры).
- SQLite (таблицы задач и лога выполнений, миграция колонок).
- Разделение: бот (`main.py`) и слой данных (`database.py`).
- Хранение токена в `.env` / `token.txt` / переменной окружения, без секретов в коде.

## Как залить проект на GitHub

1. **Создай репозиторий на GitHub:** зайди на [github.com](https://github.com) → **New repository** → имя, например `todo-bot` → **Create repository** (не добавляй README, .gitignore — они уже есть в проекте).

2. **В папке проекта открой терминал** (PowerShell или cmd) и выполни по порядку:

   ```bash
   cd C:\Users\Аламан\Desktop\Todo
   git init
   git add .
   git status
   ```
   По `git status` проверь: в списке не должно быть `.env`, `token.txt`, `todo.db` — они в `.gitignore` и не добавятся.

   ```bash
   git commit -m "Telegram To-Do bot: one-time and daily tasks, statistics"
   git branch -M main
   git remote add origin https://github.com/Alamanss/todo-bot.git
   git push -u origin main
   ```

3. Подставь **свой логин** вместо `Alamanss` в ссылке `origin`, если репозиторий под другим аккаунтом. При первом `git push` браузер может запросить вход в GitHub.

Готово: код в репозитории, секреты остаются только у тебя на компьютере.

## Лицензия

MIT — можно использовать и изменять свободно.
