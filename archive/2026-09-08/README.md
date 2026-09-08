# Архив профилей — 2026-09-08

Профили перенесены из корня без изменения содержимого. Они оставлены для
сравнения и восстановления исторических настроек, а не как действующие профили.
Основной iOS: [url-set-ios.conf](../../url-set-ios.conf).

| Файл | Назначение |
| --- | --- |
| [url-set-ios-simple-test.conf](url-set-ios-simple-test.conf) | Упрощённый S01 |
| [url-set-ios-names-test.conf](url-set-ios-names-test.conf) | Тест коротких имён N01 |
| [url-set-ios-working.conf](url-set-ios-working.conf) | Пользовательский рабочий снимок от 12:17 |
| [url-set-ios-ai-routing.conf](url-set-ios-ai-routing.conf) | Промежуточный AI-routing от 13:22 |
| [url-set-ios-ai-flat-test.conf](url-set-ios-ai-flat-test.conf) | Прямой автоматический AI-пул от 15:00 |

Имеющиеся update-url сохранены как часть истории. Они указывают на прежние пути,
поэтому не используйте их для обновления архива. Внешние RULE-SET остаются ссылками
на изменяемые источники; архивирование conf не создаёт снимки содержимого этих списков.

Исторический [разбор AI-routing](ios-ai-routing-audit.md).
Техническая fixture F08 остаётся в tools/fixtures и не является устанавливаемым профилем.
