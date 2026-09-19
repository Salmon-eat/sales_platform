# Безпека: що вже захищено в коді і що налаштувати на сервері

## Уже в коді

| Загроза | Захист |
|---|---|
| Флуд і DDoS рівня застосунку, скрейпінг, перебір | Ліміти запитів на IP в API (Redis, хвилинні вікна), окремі суворі ліміти на форми, чат, вхід; `429` + `Retry-After` |
| Повільні атаки (Slowloris), величезні запити | Таймаути Caddy, тіло запиту не більше 1 МБ |
| Сканери вразливостей (`/.env`, `/.git`, `wp-admin`, `*.php`) | Caddy одразу відповідає 404, до застосунку запит не доходить |
| XSS, впроваджені скрипти, кліккджекінг | CSP, `X-Frame-Options: DENY`, `frame-ancestors 'none'`, React екранує весь текст, JSON-LD екранується |
| Перехоплення трафіку, даунгрейд на HTTP | HTTPS від Caddy, HSTS, `upgrade-insecure-requests` |
| Підробка запитів від імені адміна (CSRF) | Токен сесії лише в заголовку до API; зміни в адмінці тільки з того самого домену (перевірка Origin) |
| Крадіжка сесії | Cookie `httpOnly` + `secure` + `SameSite=Lax`, у базі лише хеш токена, «вийти на всіх пристроях» |
| Підбір входу в адмінку | Вхід лише через Google з білим списком email; ліміт спроб на реальний IP відвідувача |
| Боти-спамери у формах | Пастка (приховане поле), ліміти на IP, Cloudflare Turnstile (вмикається ключами) |
| SQL-ін'єкції | Лише параметризовані запити (SQLAlchemy) |
| Кешування приватних даних | `Cache-Control: no-store` для адмінки, входу, чату, інтеграції з ботом |
| Атаки через залежності (supply chain) | Точні версії з хешами (`requirements.lock`, `package-lock.json`), `npm ci --ignore-scripts`, `pip-audit` і `npm audit` у CI, Dependabot |
| Злам контейнера | Процеси не від root, `no-new-privileges`, база й Redis не відкриті назовні, ротація логів |
| Витік службової інформації | Документація API вимкнена в продакшні, заголовки `Server`/`X-Powered-By` прибрані |
| Інтеграція з ботом | Секретний токен (≥32 символи), без токена ендпоінти не існують; сайт не відкриває боту жодних дій з видалення |

## Налаштувати на сервері (один раз)

1. **Cloudflare перед сайтом** (безкоштовний план): DNS домену в Cloudflare з увімкненим проксі
   (оранжева хмарка). Це захист від великих DDoS, які жоден сервер сам не витримає, і приховування IP
   сервера. Потім у `infra/caddy/Caddyfile` розкоментувати `trusted_proxies` і `client_ip_headers`, інакше
   ліміти бачитимуть IP Cloudflare замість відвідувачів. У Cloudflare: SSL/TLS → **Full (strict)**,
   Security → Bots → **Bot Fight Mode**.
2. **Turnstile**: Cloudflare → Turnstile → Add site (режим Managed) → ключі в `.env`
   (`TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`), перезібрати `web` і перезапустити `api`.
3. **Фаєрвол**: відкриті лише 22, 80, 443.
   `ufw default deny incoming && ufw allow 22/tcp && ufw allow 80,443/tcp && ufw allow 443/udp && ufw enable`.
   Увага: Docker публікує порти в обхід ufw; у продакшн-compose назовні відкритий лише Caddy.
4. **SSH**: вхід лише за ключем. У `/etc/ssh/sshd_config`: `PasswordAuthentication no`,
   `PermitRootLogin prohibit-password`, потім `systemctl restart ssh`. Плюс `apt install fail2ban`.
5. **Оновлення безпеки ОС**: `apt install unattended-upgrades && dpkg-reconfigure -plow unattended-upgrades`.
6. **Резервні копії**: щоденний `pg_dump` поза сервером (інший провайдер або сховище) і хоча б раз
   перевірити відновлення. Від шифрувальників рятує лише копія, до якої сервер не має права видаляти.
7. **Google-акаунти штату**: двофакторна автентифікація (краще passkey або ключ безпеки). Вхід в адмінку
   тримається саме на них.
8. **Секрети**: `SECRET_KEY`, `BOT_SYNC_TOKEN` — випадкові (`openssl rand -hex 32`), `.env` не в git і не в
   чатах; хтось пішов із команди — прибрати з «Штату» і змінити секрети, які він знав.
9. **Моніторинг**: безкоштовний uptime-моніторинг (наприклад UptimeRobot) на головну і `/v1/health`;
   у логах API шукати `rate limit`, `honeypot`, `turnstile` — видно, коли атакують.
