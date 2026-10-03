"""The paths of the monitor plan's working directions, as a person walks them on the portal (history 060).

python .ai-bridge/walkthroughs/walk.py .ai-bridge/walkthroughs/plan_paths.py \
    .ai-bridge/development-history/entries/060-screens
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
