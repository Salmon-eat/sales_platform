# Запуск citobazar.com: що зробити вручну

Сайт уже працює на сервері **95.179.246.45** (тимчасово: http://95.179.246.45).
Нижче — три речі, які може зробити тільки власник акаунтів: домен, вхід в адмінку, захист форм.

---

## 1. Домен через Cloudflare (30 хвилин + очікування)

### 1.1. Додати домен
1. Реєструєшся на https://dash.cloudflare.com (безкоштовний план).
2. **Add a domain** → вводиш `citobazar.com` → обираєш план **Free** → Continue.
3. Cloudflare покаже знайдені записи. **Видали всі старі A і CNAME** для `citobazar.com` і `www`
   (вони ведуть на заглушку реєстратора).

### 1.2. Додати свої записи
Кнопка **Add record**, двічі:

| Type | Name | IPv4 address | Proxy status |
|------|------|--------------|--------------|
| A | `citobazar.com` (або `@`) | `95.179.246.45` | **DNS only** (сіра хмарка) |
| A | `www` | `95.179.246.45` | **DNS only** (сіра хмарка) |

> Сіра хмарка потрібна на старті: сервер сам отримує безкоштовний сертифікат HTTPS,
> і для цього Let's Encrypt має достукатись прямо до нього.

### 1.3. Перемкнути домен на Cloudflare
1. Cloudflare покаже два свої сервери імен, приблизно такі: `xxx.ns.cloudflare.com`, `yyy.ns.cloudflare.com`.
2. Заходиш до реєстратора, де купував домен → налаштування `citobazar.com` → **Nameservers** →
   **Custom DNS** → вписуєш обидва → зберігаєш.
3. Чекаєш. Зазвичай 15 хвилин — 2 години, інколи до доби.

### 1.4. Перевірити
У командному рядку: `nslookup citobazar.com` — має показати `95.179.246.45`.
Напиши мені, коли так буде: я перевірю сертифікат і відкрию https://citobazar.com.

### 1.5. Після того, як https запрацює
У Cloudflare:
1. **SSL/TLS → Overview** → режим **Full (strict)**.
2. **SSL/TLS → Edge Certificates** → **Always Use HTTPS** = On.
3. **DNS** → обидва записи A перемкнути на **Proxied** (оранжева хмарка).
4. **Security → Bots** → **Bot Fight Mode** = On.

Після цього я вмикаю на сервері розпізнавання справжніх IP відвідувачів (два рядки в налаштуваннях Caddy),
інакше всі обмеження бачитимуть адреси Cloudflare замість людей.

---

## 2. Вхід в адмінку через Google (15 хвилин)

Адмінка зараз закрита: у неї немає паролів, вхід лише через Google.

1. https://console.cloud.google.com → вгорі створити проєкт, назва **Citobazar**.
2. **APIs & Services → OAuth consent screen**:
   - User type: **External** → Create;
   - App name: `Citobazar`; User support email: твоя пошта; Developer contact: твоя пошта → Save and continue;
   - Scopes і Test users пропускаєш → Back to dashboard;
   - натисни **Publish app** (статус має стати *In production*), інакше пускатиме лише тестові акаунти.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Application type: **Web application**;
   - Name: `Citobazar web`;
   - **Authorized JavaScript origins** → Add URI, по одному:
     - `https://citobazar.com`
     - `https://www.citobazar.com`
     - `http://localhost:3000` (для розробки)
   - Authorized redirect URIs — не потрібні, залиш порожніми;
   - **Create**.
4. Копіюєш **Client ID** (виглядає як `123456789-abc...apps.googleusercontent.com`) і даєш мені.
   Client secret не потрібен — не пересилай його.
5. Я вписую ID на сервері й перезапускаю API — вхід запрацює.
6. Скажи пошти команди (менеджерів і адміністраторів) — я додам їх у білий список.
   Твоя пошта `vadimplus57@gmail.com` вже додана як адміністратор.

> Кожен акаунт команди має мати двофакторний вхід у Google: адмінка тримається саме на ньому.

---

## 3. Захист форм Turnstile (10 хвилин, за бажанням)

Без нього працюють пастка для ботів і обмеження за IP; з ним — ще й перевірка Cloudflare.

1. Cloudflare → **Turnstile** → **Add widget**.
2. Name: `Citobazar`; Hostnames: `citobazar.com`, `www.citobazar.com`, `localhost`; Mode: **Managed** → Create.
3. Отримаєш дві величини:
   - **Site Key** — публічний, можеш просто надіслати мені;
   - **Secret Key** — таємний. Або надішли мені, або встав сам на сервері.

---

## 4. Дані компанії для юридичних сторінок

У «Політиці конфіденційності», «Правовій інформації» та «Політиці cookies» стоять заготовки у квадратних дужках:

1. повна юридична назва компанії;
2. NIF (податковий номер);
3. юридична адреса (вулиця, номер, індекс, місто, провінція);
4. пошта для звернень щодо даних (наприклад `privacidad@citobazar.com`);
5. телефон;
6. реєстраційні дані (комерційний реєстр: том, аркуш, сторінка);
7. номер агенції з працевлаштування (agencia de colocación);
8. хостинг — впишу сам (Vultr, Європа);
9. дата набрання чинності — поставлю в день запуску.

---

## 5. Що вже працює на сервері

- сайт, API, база, Redis, фоновий обробник і веб-сервер Caddy у Docker;
- 29 169 іспанських міст, довідники професій, тексти сторінок, демо-вакансії;
- фаєрвол: відкриті лише 22, 80, 443;
- вхід по SSH лише за ключем, пароль вимкнено, fail2ban, автоматичні оновлення безпеки;
- резервна копія бази щоночі о 3:30, зберігається 14 днів у `/var/backups/citobazar`.

### Корисні команди (виконую я, але хай будуть)

```bash
ssh -i ~/.ssh/citobazar_deploy root@95.179.246.45

cd /opt/citobazar
docker compose -f docker-compose.prod.yml ps                 # стан служб
docker compose -f docker-compose.prod.yml logs -f web         # логи сайту
docker compose -f docker-compose.prod.yml restart api         # перезапуск API
bash backup.sh                                                # копія бази просто зараз
```

---

## 6. Порядок дій

1. Ти: Cloudflare + NS у реєстратора (пункт 1).
2. Я: перевіряю сертифікат, відкриваю https://citobazar.com, вмикаю розпізнавання IP.
3. Ти: Google Client ID (пункт 2) → я вмикаю адмінку й додаю команду.
4. Ти: Turnstile (пункт 3) і дані компанії (пункт 4) — коли буде зручно.
5. Далі: справжні вакансії замість демо, номери WhatsApp і Viber, підключення Telegram-бота.
