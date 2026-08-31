# sr-config

Конфиги для [Shadowrocket](https://apps.apple.com/app/shadowrocket/id932747118).

## Основной конфиг

`url-set-main.conf` — самодостаточный базовый rule-конфиг и failsafe. Все
локальные и внешние списки встроены в него снапшотом; внешние источники и их
SHA-256 указаны рядом с соответствующими блоками. Поэтому он не зависит от
доступности сторонних URL списков во время работы Shadowrocket.

Ссылка для подписки (Add Config → URL):

```
https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-main.conf
```

## Конфиги с группами (iOS / macOS)

`url-set-ios.conf` и `url-set-macos.conf` — конфиги с **Proxy Group**: трафик
по категориям (AI-сервисы, Spotify, Погода, Telegram, общий прокси, блокировка рекламы) можно
переключать одним тапом в приложении — без правки правил. Есть группа
ручного выбора сервера и группа авто-выбора самого быстрого (по пингу).
По умолчанию поведение не меняется — каждая группа стартует с той же
политики, что и в основном конфиге.

Финские ноды в группах не захардкожены: есть отдельная авто-группа
«🇫🇮 Финляндия (авто)», которая сама выбирает между доступными финскими
нодами по пингу — она подставлена по умолчанию в AI-сервисы,
Spotify, Погоду, Telegram и Общий прокси.

Файлы независимые (два отдельных импорта), чтобы группы на телефоне и на
Mac переключались раздельно.

В iOS сервисные группы по умолчанию используют встроенную политику `PROXY` —
текущий сервер, выбранный на главном экране Shadowrocket. Это позволяет
использовать сервер из активной подписки без жёсткой привязки к именам групп
`DUREV` или `ALL IN 1`; финская авто-группа остаётся ручным вариантом.

На macOS Spotify намеренно направляется через `DIRECT`, а `YOUR-DUREV.COM`
остаётся доступным в ручной группе выбора сервера. Это платформенные настройки,
их не следует удалять при синхронизации конфигов.

Ссылки для подписки:

```
iOS:   https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios.conf
macOS: https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-macos.conf
```

Финская авто-группа содержит имена узлов из подписки; если после импорта
какой-то финский пункт не резолвится, открой сервер в Shadowrocket и поправь
название на точное либо оставь текущий узел `PROXY`.

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

Основной `url-set-main.conf` содержит те же локальные правила и снапшоты
внешних списков, но без `RULE-SET`, которые требуют сетевой загрузки во время
работы. При изменении внешних источников обновляй snapshot командами:

Критичные серверы каталога и загрузки watchOS, а также проверки сертификатов
Apple/DigiCert продублированы непосредственно в трёх конфигах с политикой
`DIRECT` и расположены до внешних списков. Это сохраняет проверку обновления
работоспособной даже при временной недоступности `apple.list`.

```
python3 tools/build_failsafe.py
python3 tools/validate_configs.py
```

Для проверки актуальности без записи файла:

```
python3 tools/build_failsafe.py --check
```

Проверка запускается автоматически в GitHub Actions для каждого push и pull
request. CI также проверяет доступность всех удалённых `RULE-SET` из iOS/macOS
конфигов. Проверить это локально можно командой:

```
python3 tools/check_remote_sources.py
```

Кроме проверки при изменениях, workflow
`.github/workflows/monitor-remote-sources.yml` запускается ежедневно в 09:00 по
Москве и доступен для ручного запуска через GitHub Actions. При недоступности
источников он сохраняет отчёт и создаёт/обновляет GitHub Issue; после
восстановления issue закрывается автоматически. Для email/push-уведомлений
нужно включить Watch/Actions notifications для репозитория.

Первый версионированный baseline — `v1.0.0`; для быстрого отката можно
использовать, например,
`https://raw.githubusercontent.com/squazaryu/sr-config/v1.0.0/url-set-ios.conf`.
