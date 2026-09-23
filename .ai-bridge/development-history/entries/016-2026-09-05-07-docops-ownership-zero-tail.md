# 016 — Доведение DocOps ownership до zero-tail состояния

**Период:** 2026-09-05 → 2026-09-07
**Источник:** `Восстановление контекста Sphinx Needs -- 6a9c7807-1388-83eb-9970-ded63597490f.md`

## Главное

- Повторный аудит исходного плана показал, что прежний «готово» был преждевременным: функционально пилот был зелёным, но ownership оставался недочищенным.
- Найдены три исходных хвоста:
  - `llm-router` не был Copier-update после очистки template;
  - `infra-ci` всё ещё знал детали Sphinx/JUnit/SimplePDF;
  - generic traceability/evidence presentation всё ещё частично жила в template/consumer.
- Зафиксирован правильный boundary:
  - **DocOps** владеет JUnit ingestion, generic traceability/verification/tests, Python/Gherkin source wiring и build internals;
  - **infra-ci** — только orchestration/artifacts/Pages;
  - template/consumer остаются тонкими.
- При переносе `src-trace` выяснилось, что он не только рисовал UI, но и запускал ingestion `@impl`. Это перенесли в `ternforge_docops.sphinx_python` через transient source, не возвращая логику в template.
- Для trusted docs введён явный `--live-examples`: обычный DocOps build остаётся offline, live Sphinx-Gallery разрешён только в trusted publication.
- Trusted Pages переведён на `ternforge-docops build portal`, чтобы публиковались и три Allure perspectives, а не только HTML.
- В процессе вышли ключевые линии: DocOps `0.3.x → 0.4.x`, infra-ci `5.8.x`, template `1.21.x`; `llm-router` дошёл до **v0.17.2**.

## Повторный аудит после первого «COMPLETE»

Он нашёл ещё четыре реальных хвоста:

- сам DocOps ещё не был обновлён на актуальный template;
- EXP copy-back не был recoverable/atomic для notebook + artifacts;
- обещанный legacy sweep `py-testkit / py-policy / py-runtime` не был выполнен;
- Allure BDD light/dark QA считался закрытым по пустым pre-hydration screenshots.

Исправлено:

- EXP capture стал recoverable atomic transaction;
- `py-testkit` очищен от workbench/reproduce-running-loop API и старой guidance;
- `py-policy` и `py-runtime` приведены к той же новой template/DocOps модели;
- stale source/release pins дочищены по всем согласованным tooling-репам;
- Allure BDD реально проверен **после hydration** в light и dark.

## Требования пользователя

- Не верить статусу «зелёное» без сверки именно с первоначально согласованным планом.
- Cleanup должен быть **zero-tail**, включая self-metadata, release pins, ignored/generated leftovers и update path.
- Нельзя расширять scope на другие consumers: только согласованный pilot/tooling cleanup.
- Visual QA считается доказанной только после реального рендера приложения, а не по HTTP 200 или пустому screenshot.

## Итог

Финальный аудит: согласованные 8 репозиториев clean/synchronized; активных legacy pins и старой DocOps/workbench machinery не осталось. Production `llm-router v0.17.2`, 5 EXP, dossier, Pages и Allure light/dark повторно проверены.
