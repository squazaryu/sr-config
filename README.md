# sr-config

Конфиги для [Shadowrocket](https://apps.apple.com/app/shadowrocket/id932747118).

## Основной конфиг

`url-set-main.conf` — базовый rule-конфиг. Ссылка для подписки (Add Config → URL):

```
https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-main.conf
```

## Конфиги с группами (iOS / macOS)

`url-set-ios.conf` и `url-set-macos.conf` — те же правила, что и в основном
конфиге, но с добавленными **Proxy Group**: трафик по категориям (AI-сервисы,
Spotify, Погода, Telegram, общий прокси, блокировка рекламы) можно
переключать одним тапом в приложении — без правки правил. Есть группа
ручного выбора сервера и группа авто-выбора самого быстрого (по пингу).
По умолчанию поведение не меняется — каждая группа стартует с той же
политики, что и в основном конфиге.

Финская нода в группах не захардкожена: есть отдельная авто-группа
«🇫🇮 Финляндия (авто)», которая сама выбирает между «Финляндия» и
«Финляндия 2» по пингу — она подставлена по умолчанию в AI-сервисы,
Spotify, Погоду, Telegram и Общий прокси.

Файлы независимые (два отдельных импорта), чтобы группы на телефоне и на
Mac переключались раздельно.

Ссылки для подписки:

```
iOS:   https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios.conf
macOS: https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-macos.conf
```

Список серверов в группах «🗺️ Выбор сервера» и «🚀 Авто (пинг)» собран по
названиям из приложения — если после импорта какой-то пункт группы не
резолвится (не подключается), открой сервер в Shadowrocket и поправь
название в конфиге на точное.

## Списки доменов (`lists/`)

Правила в `url-set-ios.conf` / `url-set-macos.conf` не перечисляют домены
внутри себя — они подключают отдельные `.list`-файлы через `RULE-SET`,
как это уже делалось для сторонних списков (Telegram, community/refilter
и т.п.). Так конфиг остаётся компактным, а списки доменов можно
редактировать отдельно, без изменения самого конфига:

| Файл | Политика | Содержимое |
|---|---|---|
| `lists/ai-services.list` | 🤖 AI-сервисы | OpenAI/ChatGPT, Claude, Gemini, Genspark, Manus |
| `lists/spotify.list` | 🎧 Spotify | Spotify |
| `lists/weather.list` | 🌤️ Погода | CARROT Weather / Foreca |
| `lists/telegram-domains.list` | ✈️ Telegram | доп. домены Telegram |
| `lists/telegram-ips.list` | ✈️ Telegram | доп. IP-диапазоны Telegram |
| `lists/ru-direct-domains.list` | DIRECT | Госуслуги, Яндекс, соцсети РФ, маркетплейсы, банки, связь, карты |
| `lists/ru-direct-ips.list` | DIRECT | IP госуслуг, mos.ru, Я.Маркета |
| `lists/apple.list` | DIRECT | Apple/iCloud/App Store |
| `lists/general-proxy.list` | 🌍 Общий прокси | Google/YouTube, Meta, Discord, GitHub, прочее |
| `lists/trackers.list` | 🛡️ Реклама и трекеры | доп. анти-трекинг домены |

Локальные/loopback-правила, MTProto, RU-зоны (`.ru/.su/рф/...`), GEOIP и
`FINAL` остались прямо в конфиге — они короткие и критичные, вынос не
даёт выгоды.

Основной `url-set-main.conf` списки не использует и не менялся.
