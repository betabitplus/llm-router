"""The paths of the monitor plan's working directions, as a person walks them on the portal (histories 060–062).

Each stage's folders go into its own journal entry: stage 1 into 060-screens, stage 2 into 061-screens, stage 3 into
062-screens.

python .ai-bridge/walkthroughs/walk.py .ai-bridge/walkthroughs/plan_paths.py \
    .ai-bridge/development-history/entries/060-screens 01-goal-feature-requirement ...
"""

REQ = "xpath=//table[@id='REQ_ROUTE_TIMEOUT_FALLBACK']"
PROOF = REQ + "/following::details[1]"
TIMEOUT_TILE = "a[aria-label^='Requirement: Route timeout fallback']"
REPAIR_TILE = "a[aria-label^='Requirement: Structured output repair is bounded']"

ITEMS = [
    {
        "folder": "01-goal-feature-requirement",
        "title": "01 · Цель → возможность → требование",
        "pain": "Хочу видеть, ради какой цели продукта и какой его возможности существует каждое требование, и что входит в каждую цель.",
        "answer": "У любого требования видно, ради какой цели и возможности оно существует, а у каждой цели — все её возможности и требования.",
        "steps": [
            {
                "file": "intent-map-goals", "url": "requirements/index.html",
                "view_locator": ".sd-card:has-text('Keep requests moving')", "offset": 420,
                "marks": [("a.nav-link:has-text('Intent map')", "1"), (".sd-card:has-text('Keep requests moving')", "2")],
                "title": "Intent map: цели продукта",
                "text": "① Пункт «Intent map» в шапке открывает цели продукта — зачем он существует. ② Карточка цели, например «Keep requests moving across route failures»: запрос доходит до ответа, даже когда маршруты падают. Нажимаем на неё.",
            },
            {
                "file": "idea-branch",
                "actions": [("click_box", ".sd-card:has-text('Keep requests moving')")],
                "view": "#idea-branch", "offset": 110,
                "marks": [("section#idea-branch img.graphviz", "1")],
                "title": "Ветка цели целиком",
                "text": "① Схема «Idea branch»: цель → возможность (Capability) → требования (REQ) → технические требования (TREQ). Из неё видно, из чего растёт каждое требование и что под каждой возможностью есть требования.",
            },
            {
                "file": "requirement-and-children",
                "view_locator": REQ, "offset": 110,
                "marks": [(REQ, "1"), (REQ + "/following::table[contains(@class,'needs_type_treq')][1]", "2")],
                "title": "Требование и то, что из него выведено",
                "text": "① Требование «Route timeout fallback»: что обещано и почему. ② Ниже — технические требования, выведенные из него, например «A timed-out attempt starts no further work». Цепочка видна целиком: цель → возможность → требование → техническое требование.",
            },
        ],
    },
    {
        "folder": "02-requirement-to-code-and-tests",
        "title": "02 · Требование → код и тесты",
        "pain": "По требованию хочу видеть, какой код его реализует, какие тесты его доказывают и все ли обязательные случаи доказаны.",
        "answer": "Для требования видно его код (с местом в файле), все тесты-доказательства и сколько обязательных случаев доказано: у REQ_ROUTE_TIMEOUT_FALLBACK 2 из 2.",
        "steps": [
            {
                "file": "proof-dropdown", "url": "requirements/routing.html",
                "actions": [("click", PROOF + "/summary")],
                "view_locator": PROOF, "offset": 140,
                "marks": [(PROOF + "/summary", "1"), (PROOF + "//a[contains(@href,'python-source-trace')]", "2"), ("xpath=(" + PROOF[6:] + "//a[contains(@href,'test-evidence')])[1]", "3")],
                "title": "Под требованием — его код и тесты",
                "text": "Под требованием раскрываем ① «Follow this contract to proof». ② IMPL — код, который реализует требование. ③ TEST_EVIDENCE — тесты, которые его доказывают (здесь их 8). Нажимаем на IMPL.",
            },
            {
                "file": "code-location",
                "actions": [("click", PROOF + "//a[contains(@href,'python-source-trace')]")],
                "view": "#IMPL_ROUTE_TIMEOUT_FALLBACK", "offset": 110,
                "marks": [("#IMPL_ROUTE_TIMEOUT_FALLBACK", "1")],
                "title": "Код требования",
                "text": "① Запись о коде: метка @impl в исходнике, файл и строка (source_url) и какое требование он реализует. По ссылке открывается сам код.",
            },
            {
                "file": "map-tile", "url": "verification-health-map.html#overall",
                "actions": [("hover_box", TIMEOUT_TILE)],
                "marks": [("button.tf-map-tab:has-text('Overall')", "1"), (TIMEOUT_TILE, "2")],
                "title": "На карте: плитка требования",
                "text": "Монитор показывает то же со стороны доказательств. ① Verification Health Map, общий слой: каждое требование — луч на кольцах. ② Наводим на «Route timeout fallback»: карточка показывает каждый слой (покрытие 1/1, модель ошибок 4/4, Completeness 1/1) и технические требования 2/2. Клик открывает страницу доказательств.",
            },
            {
                "file": "contract-evidence-cases", "url": "contract-evidence-route-timeout-fallback.html",
                "marks": [(".matrix-cell.pass, button.matrix-cell", "1"), ("text=Semantic coverage", "2")],
                "title": "Обязательные случаи и их тесты",
                "text": "① Матрица: на каком уровне и каким способом требование надо доказать; в клетке — сколько обязательных путей и сколько из них прошло (2 из 2). ② Справа — что требуется от доказательства: все критерии профиля доказаны (2/2), пути сохранены в прогоне.",
            },
        ],
    },
    {
        "folder": "03-test-to-requirement",
        "title": "03 · Тест → требование",
        "pain": "Есть ли тесты, которые привязаны к требованию, но ничего из обязательного не доказывают?",
        "answer": "Сейчас таких тестов 5. Каждый виден с требованием, к которому он привязан, и со ссылками на сам тест и его прогон.",
        "steps": [
            {
                "file": "explorer-unbound", "url": "verification-explorer.html#kind=unbound",
                "marks": [("button.tf-map-chip", "1"), ("span.tf-map-total", "2"), ("li.tf-ex-row >> nth=0", "3")],
                "title": "Explorer: тесты вне профилей",
                "text": "① Фильтр «Tests outside the profiles» — тесты, которые проверяют требование, но не доказывают ни одного обязательного случая. ② Их 5. ③ Каждый с требованием, к которому привязан, и ссылками на тест (Source), прогон (Allure) и запись доказательства (Evidence).",
            },
        ],
    },
    {
        "folder": "05-link-freshness",
        "title": "05 · Свежесть связей",
        "pain": "Не устарели ли доказательства: соответствуют ли они текущему коду, требованиям и прогону?",
        "answer": "Все доказательства свежие: прогон текущий («evidence all current»), слой Evidence quality зелёный — 75 требований из 75; свежесть проверяется у каждого требования отдельно.",
        "steps": [
            {
                "file": "map-stamp", "url": "verification-health-map.html#evidence",
                "marks": [("span.tf-map-stamp", "1"), ("button.tf-map-tab:has-text('Evidence quality')", "2"), (".tf-map-legend", "3")],
                "title": "Карта: свежесть всего прогона",
                "text": "① Шапка карты: какой прогон показан, когда, на каком коммите и «evidence all current» — доказательства соответствуют текущему коду и требованиям. ② Слой «Evidence quality»: здоровы ли и свежи ли доказательства. ③ Сейчас 0 провалов, 75 зелёных.",
            },
            {
                "file": "contract-tile", "url": "verification-health-map.html#evidence",
                "actions": [("hover_box", TIMEOUT_TILE)],
                "marks": [(TIMEOUT_TILE, "1"), (".tf-map-card-rows:has(span:text-is('Up to date'))", "2")],
                "title": "Свежесть у конкретного требования",
                "text": "① В том же слое каждая плитка — требование; наводим на «Route timeout fallback». ② Карточка перечисляет проверки его доказательств, среди них «Up to date 1/1»: доказательство соответствует текущему коду и ревизии требования. Устаревшее сделало бы плитку красной.",
            },
        ],
    },
    {
        "folder": "08-requirement-silent",
        "title": "08 · «Требование молчит»",
        "pain": "О каком поведении, которое видит пользователь библиотеки, требования ничего не говорят?",
        "answer": "Видно, какие требования молчат о видимом поведении (сейчас 7 требований, 16 находок), что именно не покрыто, что решили и кто решал.",
        "steps": [
            {
                "file": "map-completeness", "url": "verification-health-map.html#completeness",
                "marks": [("button.tf-map-tab:has-text('Completeness')", "1"), (".tf-map-legend", "2"), (REPAIR_TILE, "3")],
                "title": "Карта, слой Completeness",
                "text": "① Слой Completeness: закрыто ли требованием или решением всё, что видит вызывающий. ② Сейчас 7 требований красные. ③ Красная плитка — требование с открытой находкой, например «Structured output repair is bounded». Клик по ней открывает его страницу.",
            },
            {
                "file": "contract-completeness", "url": "contract-evidence-structured-output-repair.html",
                "marks": [("a.domain:has-text('Completeness')", "1")],
                "title": "Страница требования: карточка Completeness",
                "text": "① Карточка Completeness: FAIL, «4 requirements to add» — четыре находки, по которым решено добавить требование. Клик по карточке открывает их список.",
            },
            {
                "file": "explorer-silent", "url": "verification-explorer.html#kind=silent&contract=REQ_STRUCTURED_OUTPUT_REPAIR",
                "marks": [("li.tf-ex-row >> nth=0 >> span.tf-ex-state", "1"), ("li.tf-ex-row >> nth=0 >> span.tf-ex-what", "2"), ("li.tf-ex-row >> nth=0 >> span.tf-ex-why", "3"), ("li.tf-ex-row >> nth=0 >> .tf-ex-links", "4")],
                "title": "Explorer: что именно молчит",
                "text": "① Состояние: «Requirement to add» — решено добавить требование, пока не добавлено. ② Находка: о чём молчит требование, например несёт ли запрос починки схему. ③ Решение и кто решал (делегат). ④ Ссылки на код и на ответ модели, которая нашла.",
            },
        ],
    },
    {
        "folder": "10-open-questions-and-decisions",
        "title": "10 · Открытые вопросы и решения",
        "pain": "Что ещё не решено, что решено, кем и почему — и что из решённого ещё надо сделать?",
        "answer": "Нерешённых находок сейчас нет. Открыты 16 «требование добавить» и 8 «исправить код»; у 38 закрытых видны решение и причина.",
        "steps": [
            {
                "file": "requirements-to-add", "url": "verification-explorer.html#cause=toadd",
                "marks": [("button.tf-map-chip", "1"), ("span.tf-map-total", "2"), ("li.tf-ex-row >> nth=0 >> span.tf-ex-why", "3")],
                "title": "Решено добавить требование",
                "text": "① Фильтр «Why it fails: Requirement to add»: находки, по которым решили добавить требование. ② Их 16, по всем требованиям продукта. ③ У каждой — решение делегата с причиной; находка остаётся красной, пока требование не появится и тест не поймает мутанта.",
            },
            {
                "file": "fixes-to-make", "url": "verification-explorer.html#cause=tofix",
                "marks": [("button.tf-map-chip", "1"), ("span.tf-map-total", "2"), ("li.tf-ex-row >> nth=0 >> span.tf-ex-what", "3")],
                "title": "Решено исправить код",
                "text": "① Фильтр «Why it fails: Fix to make»: код, который ничего не делает, решено исправить или убрать. ② Таких 8. ③ Находка говорит, что код должен был делать и почему не делает.",
            },
            {
                "file": "closed-with-reason", "url": "verification-explorer.html#kind=silent&contract=TREQ_TOOL_REGISTRY",
                "marks": [("li.tf-ex-row >> nth=0 >> span.tf-ex-state", "1"), ("li.tf-ex-row >> nth=0 >> span.tf-ex-why", "2")],
                "title": "Закрыто с причиной",
                "text": "① «Not required» — решено, что требование не нужно; строка зелёная. ② Почему: например, ToolRegistry внутренний и вызывающему не виден. Любое закрытое решение можно перечитать здесь.",
            },
        ],
    },
    {
        "folder": "15-code-with-no-effect",
        "title": "15 · Код без эффекта",
        "pain": "Какой код ничего не делает — и что с ним решили?",
        "answer": "Видно 26 мест кода без эффекта: 8 решено исправить, 18 оставлено с причиной. Эталон с таймаутом показывает весь путь находки до зелёного.",
        "steps": [
            {
                "file": "explorer-no-effect", "url": "verification-explorer.html#kind=noeffect",
                "marks": [("button.tf-map-chip", "1"), ("span.tf-map-total", "2"), ("li.tf-ex-row >> nth=0 >> span.tf-ex-state", "3"), ("li.tf-ex-row >> nth=0 >> span.tf-ex-what", "4")],
                "title": "Explorer: код без эффекта",
                "text": "① Вид «Code with no effect» — код, удаление которого ничего не меняет для вызывающего. ② Всего 26. ③ Решение: «Fix to make» (исправить) или «Kept» (оставить). ④ Что код должен был делать и почему не делает.",
            },
            {
                "file": "contract-counter", "url": "contract-evidence-structured-schema-contract.html",
                "view_locator": ".mutant-group:has-text('Survivor judgement')", "offset": 420,
                "marks": [("div.fault-stage:has-text('No effect')", "1")],
                "title": "Счётчик на странице требования",
                "text": "① В «Survivor judgement» выбранной группы ошибок (здесь Implementation) счётчик «No effect»: 5 мест кода без эффекта; FAIL, пока хоть одно не закрыто. Другие группы — по клику на их карточку слева.",
            },
            {
                "file": "reference-found", "keep": True,
                "title": "Эталон, снимок 2 октября: найдено",
                "text": "Требование о таймауте (REQ_ROUTE_TIMEOUT_FALLBACK). ① Пять мест кода без эффекта, все «Undecided»: например, future.cancel() должен останавливать брошенную попытку, но запущенный поток так не остановить.",
            },
            {
                "file": "reference-decided", "keep": True,
                "title": "Эталон: решено делегатом",
                "text": "① Два места оставлены («Kept»: разницы для вызывающего нет), три — «Fix to make»: брошенная попытка должна перестать работать.",
            },
            {
                "file": "reference-fixed", "keep": True,
                "title": "Эталон: исправлено",
                "text": "① После исправления продукта три места исчезли вместе с кодом; остались два «Kept», оба зелёные. Требование о таймауте зелёное целиком.",
            },
        ],
    },
    {
        "folder": "17-one-outcome-per-survivor",
        "title": "17 · Один исход у каждого выжившего мутанта",
        "pain": "Каждый мутант, которого тесты не поймали, — чем он закончился?",
        "answer": "Ни один выживший не висит без исхода: на странице требования — счётчики исходов, в Explorer — исход каждого мутанта с причиной и ссылкой на ответ модели.",
        "steps": [
            {
                "file": "contract-outcomes", "url": "contract-evidence-structured-schema-contract.html",
                "view_locator": ".mutant-group:has-text('Survivor judgement')", "offset": 420,
                "marks": [(".mutant-group:has-text('Survivor judgement')", "1")],
                "title": "Исходы выживших на странице требования",
                "text": "① «Survivor judgement» выбранной группы ошибок: чем кончились выжившие мутанты — закреплены тестом (Pinned), подавлены с причиной (Suppressed), «требование молчит» (Silent requirement), «код без эффекта» (No effect), к вам (For you).",
            },
            {
                "file": "explorer-mutants", "url": "verification-explorer.html#kind=mutant&contract=REQ_STRUCTURED_SCHEMA_CONTRACT",
                "view_locator": "li.tf-ex-row:has(span.tf-ex-state:text-is('Silent requirement · Requirement to add'))", "offset": 300,
                "marks": [("span.tf-ex-state:text-is('Silent requirement · Requirement to add')", "1"), ("span.tf-ex-state:text-is('No effect · Fix to make')", "2"), ("span.tf-ex-state:has-text('Suppressed ·')", "3"), ("span.tf-ex-state:text-is('Caught')", "4")],
                "title": "Исход каждого мутанта",
                "text": "В Explorer у каждого мутанта требования ровно один исход: ① «требование молчит», решено добавить требование; ② «код без эффекта», решено исправить; ③ подавлен с причиной; ④ пойман тестом. Рядом — что изменил мутант и ссылки на код и ответ модели.",
            },
        ],
    },
    {
        "folder": "19-mutants",
        "title": "19 · Мутанты",
        "pain": "Ловят ли тесты ошибки, которые должны ловить?",
        "answer": "По каждому требованию видно, сколько посаженных ошибок пойманы, где выжившие и что с ними; у требования о таймауте пойманы все.",
        "steps": [
            {
                "file": "map-mutants-caught", "url": "verification-health-map.html#faults/detect",
                "marks": [("button.tf-map-tab:has-text('Fault model')", "1"), ("button.tf-map-choice:has-text('Mutants caught')", "2"), (".tf-map-legend", "3")],
                "title": "Карта: пойманы ли мутанты",
                "text": "① Слой «Fault model»: ловят ли тесты ошибки, которые должны. ② Вид «Mutants caught»: доля пойманных мутантов по каждому требованию. ③ Легенда объясняет цвета.",
            },
            {
                "file": "explorer-mutants", "url": "verification-explorer.html#kind=mutant&contract=REQ_ROUTE_TIMEOUT_FALLBACK",
                "marks": [("text=18 pass", "1"), ("li.tf-ex-row >> nth=5", "2"), ("li.tf-ex-row >> nth=5 >> .tf-ex-links", "3")],
                "title": "Explorer: мутанты требования",
                "text": "① У требования о таймауте 18 мутантов пойманы, 6 не считаются (подавлены с причиной или закрыты). ② Мутант: что изменено (здесь убран вызов left.set()) и что тест его поймал. ③ Ссылки на код и на отчёт мутаций.",
            },
        ],
    },
    {
        "folder": "26-evidence-trust",
        "title": "26 · Доверие к доказательствам",
        "pain": "Можно ли доверять доказательствам: откуда они и проверены ли инструменты и модели, которые их дали?",
        "answer": "У каждого доказательства видно происхождение и кто его произвёл; каждый производитель квалифицирован, и есть его карточка: роль, риск, остаточное сомнение.",
        "steps": [
            {
                "file": "contract-provenance", "url": "contract-evidence-route-timeout-fallback.html",
                "view_locator": "text=Provenance", "offset": 330,
                "marks": [(".inspector >> text=Provenance", "1"), (".inspector >> text=Producer qualification", "2")],
                "title": "У требования: происхождение и производители",
                "text": "В выбранной клетке требования: ① «Provenance» — у доказательства полное происхождение. ② «Producer qualification» — все инструменты и модели, которые его произвели, квалифицированы.",
            },
            {
                "file": "explorer-producers", "url": "verification-explorer.html#kind=producer",
                "marks": [("button.tf-map-chip", "1"), ("li.tf-ex-row >> nth=0", "2")],
                "title": "Explorer: производители доказательств",
                "text": "① Вид «Evidence producers»: все инструменты и модели, которые производят доказательства (их 22). ② У каждого — квалифицирован ли он и на чём это основано, со ссылкой на карточку доверия.",
            },
            {
                "file": "trust-record", "url": "evidence-trust.html#PRODUCER_PYTEST",
                "view": "#PRODUCER_PYTEST", "offset": 120,
                "marks": [("xpath=//*[@id='PRODUCER_PYTEST']/ancestor-or-self::section[1]", "1")],
                "title": "Карточка доверия производителя",
                "text": "① Карточка производителя: роль, чем грозит его ошибка, зачем он нужен, риск, остаточное сомнение и калибровка.",
            },
        ],
    },
    {
        "folder": "35-escapes",
        "title": "35 · Пропущенная ошибка → новая проверка",
        "pain": "Какие ошибки прошли мимо проверок и что добавили, чтобы такие ловились сами?",
        "answer": "Журнал пропусков: на каждую пропущенную ошибку — что проскочило, какая проверка должна была поймать и что добавили. Первая запись — брошенная по таймауту попытка.",
        "steps": [
            {
                "file": "escapes-journal", "url": "file:.ai-bridge/development-history/escapes.md",
                "marks": [("h2", "1"), ("li:has(> strong:text-is('Какие проверки должны были поймать:'))", "2"), ("li:has(> strong:text-is('Что добавили.'))", "3")],
                "title": "Журнал пропусков в истории разработки",
                "text": "Файл .ai-bridge/development-history/escapes.md, рядом с журналом истории. ① Запись о пропуске. ② Какие проверки должны были его поймать и почему не поймали. ③ Что добавили, чтобы такой класс ошибок ловился сам.",
            },
        ],
    },
]


# --- stage 2 (history 061): the code map and the links between code and requirements -----------------------

CODE = "code-map.html"
TIMEOUT_PAGE = "contract-evidence-route-timeout-fallback.html"
TIMEOUT_CODE = "#ce-code-req_route_timeout_fallback"


def code_tile(name):
    """A function's tile on the code map, by the name its link speaks."""
    return f"#tf-map-tiles a[aria-label^='Function: {name},']"


ITEMS_061 = [
    {
        "folder": "04-code-without-requirement",
        "title": "04 · Код без требования",
        "pain": "Хочу видеть, какой код не служит ни одному требованию, и чем служебный код отличается от ничьего.",
        "answer": "Каждая функция окрашена по тому, кому она служит: по своей метке @impl, как помощник вызывающих её функций, с записанной причиной или никому. Ничьих сейчас 61 — публичный фасад (LLMRouter, Session), сборка конфигурации и маршрутов, классы ошибок и неиспользуемый код; они остаются красными, пока требование или записанная причина их не покроют.",
        "steps": [
            {
                "file": "owner-layer", "url": CODE + "#owner",
                "marks": [("a.nav-link:has-text('Code map')", "1"), ("button.tf-map-tab:has-text('Owner')", "2"), ("#tf-map-legend", "3")],
                "title": "Карта кода: кому служит каждая функция",
                "text": "① «Code map» в шапке — продукт снизу вверх: области, модули, функции; плитка тем больше, чем больше в функции строк. ② Слой Owner: FAIL — 61 из 452 функций и классов не служат ни одному требованию. ③ Легенда: тёмно-зелёный — на функции стоит метка @impl требования, светло-зелёный — помощник: её вызывает функция требования, серый — требование не нужно и причина записана, красный — ничья.",
            },
            {
                "file": "helper", "actions": [("hover_box", code_tile("RouterRuntime._run_blocked_sync"))],
                "marks": [(code_tile("RouterRuntime._run_blocked_sync"), "1"), ("#tf-map-card", "2")],
                "title": "Помощник берёт требование у вызывающих",
                "text": "① Светло-зелёная плитка RouterRuntime._run_blocked_sync в модуле router. ② Карточка: метки на ней нет, но её вызывает функция требования REQ_SYNC_ROUTE_FALLBACK, поэтому она служит ему как помощник; видно, сколько тестов её исполняют и сколько из них — тесты её требования.",
            },
            {
                "file": "unowned", "actions": [("hover_box", code_tile("_expand_profile"))],
                "marks": [(code_tile("_expand_profile"), "1"), ("#tf-map-card", "2")],
                "title": "Ничья функция",
                "text": "① Красная плитка _expand_profile в модуле routes: она разворачивает профиль маршрута в список маршрутов. ② Карточка: ни на ней, ни на вызывающих её функциях нет метки @impl, поэтому она не служит ни одному требованию, хотя её исполняют 234 теста. Так же ничьи и LLMRouter.query, главный вход в продукт, и весь публичный фасад.",
            },
            {
                "file": "unowned-table", "url": CODE + "#owner/table?owner=none",
                "marks": [("button.tf-map-chip", "1"), ("#tf-map-summary", "2"), ("#tf-map-list tr.tf-map-list-row >> nth=0", "3")],
                "title": "Все ничьи — списком",
                "text": "Вид «Table» слоя Owner с фильтром ① «Serves no requirement». ② Их 61, по областям и модулям. ③ В строке — функция и её место в коде, сколько тестов её исполняют и почему не исполняются её строки; CSV выгружает список.",
            },
        ],
    },
    {
        "folder": "06-link-confirmed-by-execution",
        "title": "06 · Связь подтверждена исполнением",
        "pain": "Метка @impl говорит, что функция реализует требование. Хочу видеть, исполняют ли эту функцию тесты самого требования.",
        "answer": "По каждой функции требования видно, исполняют ли её его тесты. У REQ_ROUTE_TIMEOUT_FALLBACK одну из 17 функций (_normalize_tool_choice) не исполняет ни один тест её требований: её связь с требованием не подтверждена исполнением. Всего таких функций 46.",
        "steps": [
            {
                "file": "contract-code", "url": TIMEOUT_PAGE, "view": TIMEOUT_CODE, "offset": 270,
                "marks": [(TIMEOUT_CODE + " .section-head", "1"), (TIMEOUT_CODE + " .signal-card", "2"), (TIMEOUT_CODE + " tr.not-met >> nth=0", "3")],
                "title": "Страница требования: его код",
                "text": "Страница доказательств REQ_ROUTE_TIMEOUT_FALLBACK, раздел ① «Code»: 17 функций служат требованию — одна по его метке, 16 как помощники. ② «Run by its tests» 16 из 17: функцию с меткой обязаны исполнить тесты этого требования, помощника — тесты любого его требования. ③ Красная строка: эту функцию не исполняет ни один такой тест. Общий статус требования раздел не меняет: это сведения, а слой на карте кода красный.",
            },
            {
                "file": "map-run-layer", "actions": [("click", TIMEOUT_CODE + " a.section-link:has-text('Code map')")],
                "marks": [("button.tf-map-chip", "1"), ("button.tf-map-tab:has-text('Run by its tests')", "2"), (code_tile("_normalize_tool_choice"), "3")],
                "title": "Тот же код на карте",
                "text": "① Карта открылась с фильтром по требованию: его функции яркие, остальные приглушены. ② Слой Run by its tests. ③ Красная плитка — та самая функция, которую тесты её требований не исполняют.",
            },
            {
                "file": "not-run-card", "actions": [("hover_box", code_tile("_normalize_tool_choice"))],
                "marks": [(code_tile("_normalize_tool_choice"), "1"), ("#tf-map-card", "2")],
                "title": "Почему красная",
                "text": "① _normalize_tool_choice. ② Карточка: её исполняют тесты других требований, но ни один тест требований, которым она служит, — связь не подтверждена исполнением.",
            },
        ],
    },
    {
        "folder": "07-marker-covers-function",
        "title": "07 · Метка относится ко всей функции",
        "pain": "Метка @impl стоит на одной строке. Хочу видеть, что она охватывает и какую функцию относит к требованию.",
        "answer": "Видно, где стоит каждая метка и что она охватывает: для владения метка на одной строке относит к своему требованию всю функцию, а кампания мутаций по-прежнему сажает мутантов только в строки самой метки.",
        "steps": [
            {
                "file": "marker-scope", "url": CODE + "#owner:llm_router._internal.runtime.router.RouterRuntime._call_sync_with_timeout",
                "marks": [(code_tile("RouterRuntime._call_sync_with_timeout"), "1"), ("#tf-map-card", "2")],
                "title": "Метка и функция",
                "text": "① RouterRuntime._call_sync_with_timeout. ② Карточка: метка IMPL_ROUTE_TIMEOUT_FALLBACK стоит на всей функции, а IMPL_TIMED_OUT_ATTEMPT_LEFT — на одной строке 448; для своего требования каждая охватывает всю функцию, поэтому функция служит обоим.",
            },
        ],
    },
    {
        "folder": "14-unused-code",
        "title": "14 · Неиспользуемый код",
        "pain": "Хочу видеть код, которым ничто не пользуется, и чтобы его не становилось больше.",
        "answer": "Неиспользуемый код виден цветом и списком: сейчас 7 — четыре функции и три класса ошибок, которые никто не бросает. Гейт держит это число: оно может только уменьшаться, а рост без записанной причины валит гейт.",
        "steps": [
            {
                "file": "used-layer", "url": CODE + "#used",
                "marks": [("button.tf-map-tab:has-text('Used')", "1"), ("#tf-map-legend", "2")],
                "title": "Слой Used",
                "text": "① Слой Used: FAIL — 7 из 452. ② Красным — функции и классы, которые ничто в пакете не использует (их находит vulture); то, что пакет отдаёт наружу, считается используемым.",
            },
            {
                "file": "ratchet", "actions": [("press", "f")],
                "marks": [("p.tf-cm-ratchet", "1"), ("button.tf-map-option[data-facet='used'][data-value='unused']", "2")],
                "title": "Число, которое может только уменьшаться",
                "text": "Фильтры слоя Used: ① «May only fall: held at 7» — гейт держит это число; оно может только уменьшаться, а рост без записанной причины валит гейт. ② «Nothing uses it 7» — нажатие оставит на карте только их.",
            },
            {
                "file": "unused-table", "url": CODE + "#used/table?used=unused&group=none", "actions": [("press", "f")],
                "marks": [("#tf-map-summary", "1"), ("#tf-map-list tbody", "2")],
                "title": "Все семь списком",
                "text": "① 7 функций и классов. ② Среди них три класса ошибок, которые никто не бросает (RuntimeBoundaryUnavailableError, AllRoutesBlockedError, KeyResolutionError), и функции, которые никто не вызывает; у каждой видно её место в коде.",
            },
        ],
    },
    {
        "folder": "16-unexecuted-lines-causes",
        "title": "16 · Разбор неисполняемых строк на 4 причины",
        "pain": "Хочу знать про каждую строку, которую не исполняет ни один тест, почему: нет теста, нет требования, код лишний или отключён намеренно.",
        "answer": "Каждая неисполняемая строка получает одну причину: сейчас 299 строк без теста своего требования, 72 строки без требования, 6 лишних (неиспользуемый и недостижимый код) и 0 отключённых намеренно. По функции видно, какие именно строки и почему.",
        "steps": [
            {
                "file": "lines-layer", "url": CODE + "#lines",
                "marks": [("button.tf-map-tab:has-text('Unexecuted lines')", "1"), ("#tf-map-legend", "2")],
                "title": "Почему строки не исполняются",
                "text": "① Слой Unexecuted lines: 377 строк не исполняет ни один тест. ② У каждой строки одна причина (DO-178C 6.4.4.3): нет теста, нет требования, лишний код, отключено намеренно; плитка окрашена самой тяжёлой причиной в функции.",
            },
            {
                "file": "line-causes", "actions": [("hover_box", code_tile("_native_part"))],
                "marks": [(code_tile("_native_part"), "1"), ("#tf-map-card", "2")],
                "title": "Строка → причина",
                "text": "① _native_part в aistudio. ② Карточка: строки 236 и 264 не исполняет ни один тест — нет теста; строки 280 и 281 — лишние: это недостижимый код после return, его не видит coverage.py, но находит vulture.",
            },
            {
                "file": "lines-table", "url": CODE + "#lines/table",
                "marks": [("#tf-map-list th:has-text('Causes')", "1"), ("#tf-map-summary", "2")],
                "title": "Все причины в таблице",
                "text": "① Столбец «Causes»: по каждой функции — сколько строк и по какой причине. ② Итог по всему продукту; CSV выгружает каждую функцию с числом строк по причинам.",
            },
        ],
    },
    {
        "folder": "37-links-both-ways",
        "title": "37 · Связи в обе стороны на сайте",
        "pain": "Хочу переходить от функции к требованию, которому она служит, и от требования — к его функциям.",
        "answer": "Между кодом и требованием можно ходить в обе стороны: из таблицы карты кода — на страницу требования, со страницы требования — на карту, где горят только его функции, а имя функции открывает её на карте.",
        "steps": [
            {
                "file": "code-to-requirement", "url": CODE + "#owner/table?req=REQ_ROUTE_TIMEOUT_FALLBACK",
                "marks": [("button.tf-map-chip", "1"), ("td.tf-cm-serves a:has-text('REQ_ROUTE_TIMEOUT_FALLBACK') >> nth=0", "2")],
                "title": "От функции к требованию",
                "text": "Таблица карты кода с фильтром ① по требованию. ② В столбце «Serves» требование — ссылка на его страницу доказательств. Нажимаем.",
            },
            {
                "file": "requirement-to-code", "actions": [("click", "td.tf-cm-serves a:has-text('REQ_ROUTE_TIMEOUT_FALLBACK') >> nth=0")],
                "view": TIMEOUT_CODE, "offset": 270,
                "marks": [(TIMEOUT_CODE + " a.section-link:has-text('Code map')", "1"), (TIMEOUT_CODE + " tbody tr >> nth=0", "2")],
                "title": "От требования к коду",
                "text": "Страница требования, раздел «Code»: ① ссылка «Code map» ведёт обратно на карту, где горят только функции этого требования; ② имя функции открывает её на карте, ссылка «Source» — её код.",
            },
        ],
    },
]

ITEMS += ITEMS_061


# --- stage 3 (history 062): coverage of lines and branches, exceptions, metric bases, releases ------------------------

EXPLORER = "verification-explorer.html"
RELEASES = "releases.html"


def kind_button(kind):
    """The explorer's kind switch button for one kind of item."""
    return f"#tf-map-kinds button[data-value='{kind}']"


def explorer_row(text):
    """An explorer row by the text it shows."""
    return f"li.tf-ex-row:has-text('{text}') >> nth=0"


ITEMS_062 = [
    {
        "folder": "18-line-and-branch-coverage",
        "title": "18 · Покрытие строк и ветвей",
        "pain": "Хочу видеть покрытие каждой функции и модуля не только по строкам, но и по ветвям, и отдельно — исполняют ли тесты строки, которые меняет эта ветка.",
        "answer": "Прогон тестов теперь меряет ветви. Тесты проходят 834 из 1044 ветвей (79%) и исполняют 2217 из 2592 строк функций. Из 145 строк, которые ветка меняет против main, тесты не исполняют 10 — в пяти функциях; например, весь новый код _media_content_part в openai_compatible.",
        "steps": [
            {
                "file": "branches-view", "url": CODE + "#lines/branches",
                "marks": [("button.tf-map-tab:has-text('Unexecuted lines')", "1"), ("[data-map-view='lines/branches']", "2"), ("#tf-map-legend", "3")],
                "title": "Карта кода: ветви",
                "text": "① Слой Unexecuted lines получил ещё два вида. ② Вид «Branches»: функция окрашена по тому, проходят ли тесты все её ветви. ③ Легенда: 115 функций с непройденными ветвями, 115 — все ветви пройдены, у 222 ветвей нет; всего пройдено 834 из 1044 ветвей.",
            },
            {
                "file": "branch-card", "actions": [("hover_box", code_tile("RouterRuntime._run_sync"))],
                "marks": [(code_tile("RouterRuntime._run_sync"), "1"), ("#tf-map-card", "2")],
                "title": "Какая ветвь не пройдена",
                "text": "① RouterRuntime._run_sync. ② Карточка, раздел «Coverage»: строк исполнено 39 из 41, ветвей пройдено 7 из 8, не пройдена ветвь 219→220 — переход, которого ни один тест не делает.",
            },
            {
                "file": "new-lines-view", "url": CODE + "#lines/new",
                "marks": [("[data-map-view='lines/new']", "1"), ("#tf-map-legend", "2"), (code_tile("_media_content_part"), "3")],
                "title": "Новые строки отдельно",
                "text": "① Вид «New lines»: только строки, которые ветка меняет против своей точки ветвления от main. ② 135 из 145 новых строк тесты исполняют; 5 функций с неисполненными новыми строками красные, функции без новых строк серые. ③ Красная плитка _media_content_part: её новый код не исполняет ни один тест.",
            },
            {
                "file": "new-lines-card", "actions": [("hover_box", code_tile("_media_content_part"))],
                "marks": [("#tf-map-card", "1")],
                "title": "Что именно не исполнено",
                "text": "① Карточка _media_content_part: новых строк 5, исполнено 0 — сюда стоит дописать тест прежде, чем ветка уйдёт в main.",
            },
            {
                "file": "coverage-table", "url": CODE + "#lines/table",
                "marks": [("#tf-map-list th:has-text('Lines run')", "1"), ("#tf-map-list th:has-text('Branches')", "2"), ("#tf-map-list th:has-text('New lines')", "3"), ("#tf-map-list tr.tf-map-list-group >> nth=0", "4")],
                "title": "Таблица: покрытие функции и модуля",
                "text": "Вид «Table»: у каждой функции ① исполненные строки, ② пройденные ветви и ③ исполненные новые строки — числом и долей. ④ Строка группы — те же числа по модулю и области; сортировка по колонке выводит наверх наименее покрытые.",
            },
        ],
    },
    {
        "folder": "30-exceptions-registry",
        "title": "30 · Единый реестр исключений",
        "pain": "Исключения разбросаны: вердикты по мутантам, закрытые находки, # noqa и # pragma в коде, пропуски тестов. Хочу видеть их все в одном месте, у каждого — причину и срок, и чтобы их число не росло незаметно.",
        "answer": "Все 108 исключений в одном списке Explorer: 51 мутант, исключённый вердиктом или решением, 38 закрытых находок и 19 исключений в коде. У каждого — причина, кто решил, когда и до какого срока действует. Вердикт модели действует, пока не изменился её вопрос; остальное — 90 дней от решения. Число по каждому типу может только уменьшаться: рост без записанной причины валит гейт.",
        "steps": [
            {
                "file": "exceptions-kind", "url": EXPLORER + "#kind=exception", "actions": [("js", "window.scrollTo(0, 0)"), ("press", "f")],
                "marks": [(kind_button("exception"), "1"), ("p.tf-cm-ratchet", "2"), ("#tf-ex-summary", "3")],
                "title": "Explorer → Exceptions",
                "text": "① Вид «Exceptions» в переключателе панели фильтров: 108 исключений любого рода. ② Строка «May only fall»: сколько исключений каждого типа держит гейт — Judged out 50, Decided out 1, Not required 20, Kept 18, Tool comment 16, Test skip 1, Pin outside the oracle rule 1, Ignored import 1. ③ Ни одно не падает: у каждого есть причина и срок не истёк (N/A — мутанты, которых исключение выводит из счёта).",
            },
            {
                "file": "code-exception", "url": EXPLORER + "#kind=exception&exception=comment",
                "view_locator": explorer_row("registry.py:74"), "offset": 220,
                "marks": [(explorer_row("registry.py:74"), "1")],
                "title": "Исключение в коде: причина и срок",
                "text": "① # noqa: E402 в registry.py:74: что исключено — сама строка кода (импорт адаптера), срок — «Until 1 Jan 2027», ниже причина, которую записал делегат, проверив код: импорт стоит рядом с регистрацией, а перенос наверх модуля ничего не ломает (проверено), — это выбор раскладки, а не необходимость. Source ведёт на строку.",
            },
            {
                "file": "verdict-exception", "url": EXPLORER + "#kind=exception&exception=judged",
                "marks": [("li.tf-ex-row >> nth=0", "1")],
                "title": "Мутант, исключённый вердиктом модели",
                "text": "① Выживший мутант, которого модель признала эквивалентным или нерелевантным, а модель другого семейства подтвердила. Срок у такого исключения — «holds while its question is unchanged»: вердикт действует, пока не изменились код, требование и тесты, о которых спрашивали; изменение задаёт вопрос заново.",
            },
            {
                "file": "finding-exception", "url": EXPLORER + "#kind=exception&exception=not-required",
                "marks": [("li.tf-ex-row >> nth=0", "1")],
                "title": "Закрытая находка — тоже исключение",
                "text": "① Молчащее требование, которое делегат решил не вводить: «Not required · holds until …» — решение пересматривается через 90 дней. Тот же пункт стоит и в своём виде Silent: одна запись, два пути к ней.",
            },
            {
                # A state made on purpose and undone (history 062): one record without its reason, one dated past its days.
                "file": "failing-exceptions", "keep": True,
                "title": "Проверка на поломке: без причины и просроченное",
                "text": "Нарочно сломано и откачено: у одной записи убрана причина, другой поставлена дата 1 июня. ① Фильтры: вид «Exceptions» и Review — «No reason» и «Review overdue». ② Оба исключения красные: «No reason» — у global в config/state.py причина не записана (видно только, когда написана строка), ссылка ведёт к файлу записей; «Overdue since 30 Aug 2026» — решению по PLR0913 в router.py больше 90 дней. ③ Счётчик: 2 fail.",
            },
        ],
    },
    {
        "folder": "31-metric-base-guard",
        "title": "31 · Защита метрик от подкрутки",
        "pain": "Число может улучшиться не потому, что продукт стал лучше, а потому что ослабили то, с чем его сравнивают: подняли порог, добавили исключение, убрали обязательный путь из профиля. Хочу видеть, когда базу метрики меняли вместе с кодом.",
        "answer": "Explorer → «Base changes» перечисляет каждый коммит ветки, который менял базу метрики, с тем, ослабил он её или ужесточил. Из 32 изменений 16 ослабили базу в одном коммите с кодом или тестами — они красные; например, e9e0e75 снизил число обязательных путей двух критериев видео с 4 до 3. Гейт это не валит: отметка просит человека посмотреть.",
        "steps": [
            {
                "file": "base-changes", "url": EXPLORER + "#kind=basechange",
                "marks": [(kind_button("basechange"), "1"), ("#tf-ex-summary", "2"), ("li.tf-ex-row.failed >> nth=0", "3")],
                "title": "Explorer → Base changes",
                "text": "① Вид «Base changes»: коммиты ветки, менявшие то, с чем сравниваются числа, — закреплённые числа, записи исключений, вердикты и решения по выжившим, профили проверки, настройки инструментов, CI. ② 16 красные: база ослаблена в том же коммите, что и код. ③ Каждая строка говорит, что именно ослаблено.",
            },
            {
                "file": "looser-with-code", "url": EXPLORER + "#kind=basechange&direction=looser&withcode=yes", "actions": [("js", "window.scrollTo(0, 0)")],
                "marks": [("#tf-map-chips button:has-text('Direction')", "1"), ("#tf-map-chips button:has-text('With the code')", "2"), ("#tf-ex-summary", "3")],
                "title": "Только ослабленное вместе с кодом",
                "text": "Фильтры ① «Direction: Looser» и ② «With the code: Changes code or tests too». ③ Таких изменений 16: в каждом коммите вместе с кодом или тестами ослаблена база — добавлены исключения, профиль просит меньше или инструмент исключает больше. Длинный перечень по вердиктам сведён по видам баз: сколько файлов и в какую сторону, первые три — поимённо.",
            },
            {
                "file": "e9e0e75", "view_locator": explorer_row("e9e0e75"), "offset": 220,
                "marks": [(explorer_row("e9e0e75"), "1")],
                "title": "Пример: меньше путей вместе с кодом",
                "text": "① Коммит e9e0e75: профили проверки просят у двух критериев видео 3 пути вместо 4, а настройки pytest изменены, — в том же коммите, что 37 файлов кода и тестов. Ссылка Commit открывает коммит целиком.",
            },
            {
                "file": "tighter", "url": EXPLORER + "#kind=basechange&direction=tighter",
                "marks": [("li.tf-ex-row >> nth=0", "1")],
                "title": "Ужесточение и перенос не красные",
                "text": "① Коммит, который только добавил требования или опустил закреплённые числа, — зелёный. Перенос критерия или класса ошибок в выведенное техническое требование в том же коммите не считается ослаблением.",
            },
        ],
    },
    {
        "folder": "38-release-snapshot",
        "title": "38 · Снимок на релиз",
        "pain": "Хочу знать, что было открыто в момент релиза: какие проверки падали и какие исключения действовали, — и что с тех пор исправлено.",
        "answer": "Первый прогон монитора на теге релиза замораживает снимок: числа, все падающие пункты и все действующие исключения; по запросу снимок можно снять и между релизами. Снимок не переписывается. Страница Releases перечисляет снимки, а каждый открывается списком Explorer «как было», с отметкой, что стало с каждым пунктом.",
        "steps": [
            {
                "file": "releases-page", "url": RELEASES,
                "marks": [("nav button:has-text('More')", "1"), ("table.tf-rel-table tbody tr >> nth=0", "2")],
                "title": "Releases: снимки",
                "text": "① Страница Releases — в меню «More» шапки. ② Снимок v0.24.3-75-g12a7d77 — прогон на коммите 12a7d77, на 75 коммитов позже релиза v0.24.3; входы прогона ровно совпадают с файлами коммита. Видно, сколько меток Health Map падало, сколько пунктов было открыто, сколько исключений действовало и что с тех пор исправлено.",
            },
            {
                "file": "snapshot-list", "actions": [("click", "table.tf-rel-table a.tf-rel-name >> nth=0")],
                "marks": [("#verification-explorer h1", "1"), ("p.tf-release-lead", "2"), ("#tf-map-stamp", "3")],
                "title": "Что было открыто",
                "text": "① Список снимка — тот же Explorer, но с пунктами, какими они были. ② Под заголовком: из какого прогона и коммита снят снимок и что стало с его падающими пунктами с тех пор. ③ Строка прогона называет снимок.",
            },
        ],
    },
]
HEALTH = "verification-health-map.html"
ITEMS_062.insert(3, {
    "folder": "36-trends",
    "title": "36 · Тренды и регресс",
    "pain": "Хочу видеть у каждого числа, куда оно идёт от прогона к прогону, и чтобы рост того, что падает, был красным; маленькая линия — с понятным путём к подробностям.",
    "answer": "У каждой карточки слоя в правом верхнем углу — короткая линия числа по сохранённым прогонам со значком «развернуть» (две стрелки наружу): это кнопка, как focus mode в Power BI или развёртывание виджета в Datadog, а не «?» с пояснением. Рост красный, падение зелёное. По клику — плашка: крупный график, каждый прогон с числом, шагом, коммитом и тем, совпадали ли входы с коммитом, и кнопка «что изменилось». В таблице All layers у каждого слоя та же линия и разброс. Числа берутся из истории монитора (`monitor-history.jsonl`).",
    "steps": [
        {
            "file": "cards", "url": HEALTH, "actions": [("js", "window.scrollTo(0, 0)")],
            "marks": [("[data-trend='overall']", "1"), ("[data-trend='faults']", "2")],
            "title": "Линия тренда в карточке слоя",
            "text": "① У каждой карточки в правом верхнем углу — линия её числа за последние сохранённые прогоны и значок «развернуть» — две стрелки наружу. ② Fault model: подъём до 63 красный (стало хуже), спуск зелёный, ровно — серый; точка в конце — этот прогон.",
        },
        {
            "file": "hover", "actions": [("hover", "[data-trend='faults']")],
            "marks": [("[data-trend='faults']", "1"), ("#tf-map-hint", "2")],
            "title": "Это кнопка, а не пояснение",
            "text": "① При наведении линия со значком становится кнопкой (рамка и фон, как у других кнопок карты). ② Подсказка: сколько сейчас, шаг от прошлого прогона, минимум и максимум, и что по клику — подробности.",
        },
        {
            "file": "details", "actions": [("click", "[data-trend='faults']")],
            "marks": [(".tf-trend-chart", "1"), (".tf-trend-summary", "2"), (".tf-trend-runs", "3"), ("[data-trend-changes]", "4")],
            "title": "Плашка с подробностями",
            "text": "Открывается под карточкой, сама карточка с её числом видна. ① Крупный график: красное — рост, зелёное — падение; полые точки — прогоны, сохранённые до начала истории, их коммит не записан. ② Сейчас 34 из 65, без изменения, максимум 63. ③ Каждый прогон: число, шаг, коммит, совпадали ли входы с коммитом. ④ Одна кнопка — подсветить на карте, что изменилось с прошлого прогона. Закрывается Esc, щелчком вне или крестиком; фокус возвращается на кнопку.",
        },
        {
            "file": "all-layers", "actions": [("press", "Escape"), ("click", "#tf-map-table-toggle")],
            "marks": [("#tf-map-table-toggle", "1"), (".tf-map-row-trend >> nth=0", "2"), (".tf-map-row-trend >> nth=2", "3")],
            "title": "Все тренды сразу: таблица All layers",
            "text": "① «All layers» открывает таблицу слоёв. ② У каждого слоя справа — та же линия и разброс за прогоны: Overall 39–75. ③ Fault model 34–63. У видов-мер (Depth, Test level…) истории пока нет — ячейка пустая.",
        },
        {
            "file": "code-map", "url": CODE + "#owner", "actions": [("js", "window.scrollTo(0, 0)"), ("click", "[data-trend='owner']")],
            "marks": [("[data-trend='owner']", "1"), (".tf-trend-chart", "2")],
            "title": "То же на Карте кода",
            "text": "① Карта кода — тот же движок: у слоёв Owner, Run by its tests и Used есть линия. ② Пока это два прогона — ровно 61. Слой строк получит линию со следующего прогона: до сегодня число строк в историю не писалось.",
        },
    ],
})
ITEMS += ITEMS_062
