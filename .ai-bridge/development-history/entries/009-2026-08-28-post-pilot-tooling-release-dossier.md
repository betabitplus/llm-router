# 009 — Дополнительные reader/tooling слои и release dossier

**Период:** 2026-08-28
**Источник:** `Восстановление контекста Ternforge -- 6a91608b-a4cc-83eb-9369-15a962f5dbfa.md`

## Главное

- После foundation добавлялись не новые source-of-truth, а **reader/presentation слои**: GherkinLens, `ubCode`, `ubConnect`, `sphinx-llm`, SimplePDF.
- Выявился важный runtime split:
  - live/provider-heavy документация удобнее на доверенном macOS runner;
  - deterministic PDF/rendering — на Ubuntu.
- В production docs обнаруживался provider drift; live publication должна уметь показывать реальное текущее состояние, а не скрывать нестабильность.
- Введён release dossier как воспроизводимый артефакт релиза.
- `llm-router` дошёл до **v0.13.2**.

## Требования пользователя

- Reader/UX плагины не должны становиться новым источником истины.
- Публикация должна сохранять forensic/evidence артефакты.
- Разделять среды исполнения по реальным техническим ограничениям, а не пытаться заставить один runner делать всё.
- Live provider drift нужно показывать честно.

## Результат

Система получила несколько способов чтения одного и того же engineering graph и отдельный reproducible release-dossier path.
