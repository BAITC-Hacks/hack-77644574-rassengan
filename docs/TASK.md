# TASK: the single source of truth for what we must build

> Both Codex and Claude Code read this file. Full verbatim spec: `docs/CASE_SPEC_RU.md`.

## 1. Task identity
- Chosen task: **Умный подбор подрядчиков (#79-lite)**: smart event-contractor matching
- Track: Креативные индустрии (Creative industries)
- Link or file with the original description: `docs/CASE_SPEC_RU.md` (copied verbatim from the official case Google Doc)
- Competition: 13:00–18:00 Astana, 23 Sep 2026; hourly checkpoints 14:00, 15:00, 16:00, 17:00, 18:00; 18:00 state is final
- Team: 2 people (tech lead / main dev + junior dev)

## 2. Mandatory conditions (verbatim from the spec, RU)
1. Вход: город, дата мероприятия, тип мероприятия, категория подрядчика, бюджет (₸). Опционально — длительность (ч) и язык.
2. Выход: до 3 карточек. В карточке — имя, категория, город, цена и 1–2 предложения объяснения: совпадение по бюджету, формату, языку, длительности или по смыслу описания. Общих фраз вроде «отличный выбор для вашего мероприятия» быть не должно.
3. Подрядчик, занятый на эту дату, в выдачу не попадает. Площадки лежат в том же каталоге и с тем же календарём.
4. Подходящих меньше трёх — показать сколько есть и сказать, почему меньше.
5. Детерминизм: тот же запрос — тот же порядок карточек.
6. Три исхода различимы для пользователя явно: подобрали / в этом городе такой категории нет / кандидаты есть, но ни один не проходит по условиям (заняты на дату, не тянут бюджет, не берут этот формат).

### Definition of Done (checked live, not on slides)
- DoD1. Ответ на запрос приходит за разумное время (ориентир — до 10 секунд).
- DoD2. Объяснения не взаимозаменяемы: если стереть имена, карточки одного запроса нельзя перепутать между собой.
- DoD3. Повторный запуск с теми же параметрами даёт тот же порядок.
- DoD4. Один и тот же запрос на две разные даты даёт разную выдачу, и в объяснении видно, что дело в занятости.
- DoD5. Показаны минимум три запроса: плотная категория на осеннюю дату (Ведущий — 15, Фотограф — 12, Банкетный зал — 8); редкая категория (Флорист, Декоратор, Подарки и сувениры, Ведущий церемонии, Фото и видеобудки, Отель, Инструменталист — по 3); запрос без результата.
- DoD6. Пустой результат объяснён словами, а не пустым экраном и не ошибкой.
- DoD7. Команда может объяснить жюри, что происходит внутри пайплайна.

### Out of scope (per spec)
- Booking, requests, notifications to contractors: recommendation only.
- Pretty UI: explanation quality wins over interface.
- Fine-tuning on 66 records. Ready embeddings and LLM via API are allowed.

### Judge priority (per spec)
Quality of explanations > honest handling of rare, busy and empty categories > speed > interface.

## 3. Required inputs, outputs and data
- Input: city, date, event type (format), contractor category, budget ₸; optional duration (h), language.
- Output: up to 3 cards {name, category, city, price, 1–2 sentence specific explanation} + an outcome status + a reason when fewer than 3.
- Data: `hackathon-dataset-anonymized.jsonl`: 66 profiles (also .csv and HTML preview). Fields: id, anon_name, categories[], city (Алматы/Астана/Зарубежье), price_from_kzt, event_formats[] (свадьба, той, корпоратив, конференция, юбилей, день рождения), languages[], max_hours (null = not presence-bound), busy_dates (window 23.09.2026–31.12.2026), description (RU free text), flags synthetic / city_imputed / price_imputed.
- Our own synthetic profiles are allowed in the same format with `synthetic: true`; the demo must show which profiles are real and which are ours.
- Calendar load: Sep–Nov 30–50% busy, Dec 70–80% (in December, dense categories have almost no one free on weekends: that's the season, not a bug).

## 4. Required or provided tools
- No required provider. LLM via API allowed (we use OpenAI; key from env `OPENAI_API_KEY`, never committed).
- Must work without any personal account (rule 5.6.6): without a key, a deterministic template explainer is used; README documents both modes.

## 5. Deliverables
- [ ] Working project in the team repo
- [ ] README (install, run, architecture, pipeline explanation, demo queries)
- [ ] Demo: at least the 3 required queries + the "two dates" query, live
- [ ] Other: none

## 6. Our decision
- Main scenario: request (city, date, event type, category, budget[, hours, language]) → hard filters (city, category, busy date, format, budget, hours, language) with a reason counted for every rejected candidate → deterministic scoring and ranking (stable tie-break by id) → top ≤3 → explanation per card built from the concrete matched facts (LLM rewrites facts into 1–2 sentences; deterministic template fallback) → one of three explicit outcomes + "why fewer than 3" summary from the rejection counts.
- Stack: Python 3.9+, FastAPI + a single static HTML page, pytest. No database.
- Explicitly NOT doing: booking, auth, fancy UI, fine-tuning, vector DB.
- Assumptions: budget means the client's max budget and matches if price_from_kzt ≤ budget; price_imputed/city_imputed flags are shown in the card; "Зарубежье" is treated as its own city value.

## 7. Questions asked to organizers and their answers
| Question | Answer | Who / when |
|---|---|---|
| Where is the dataset file for this case? | | |
