# Источники новой серии

Проверено 4 ноября 2026 года. 40 постов в `advanced.json`: сначала 20 по ВЛ 10 кВ, затем 20 по промышленной сети 0,4 кВ. Поле `source_ids` связывает пост с первичными источниками. Численные примеры составлены отдельно как учебные модели, без выбора конкретного изделия. Условия реальной сети и критерии проекта должны быть заданы до назначения уставок.

- N1 — [NOJA Power: назначение защитных функций](https://www.nojapower.com/expertise/2021/protection-feature-application-summary-us). Фазные, земляные и направленные функции; пределы обычной EF при неэффективно заземлённой нейтрали.
- N2 — [NOJA Power: направленная защита ОЗЗ и Cos Phi](https://www.nojapower.com/expertise/noja-power-releases-cos-phi-earth-fault-algorithm-for-recloser-controller-package). Компенсированная нейтраль, чувствительность, угловые рабочие области. Доступность конкретного алгоритма проверяется по терминалу.
- N3 — [NOJA Power: согласование защит при распределённой автоматике](https://www.nojapower.com/expertise/2019/protection-grading-distributed-automation-iv-us). Изменение топологии и направления питания, интервалы согласования, секционализирующая логика.
- S1 — [Schneider Electric: выбор автоматического выключателя](https://www.electrical-installation.org/enwiki/Selection_of_a_circuit-breaker). Нагрузка, кабель, ток КЗ, среда и координация.
- S2 — [Schneider Electric: минимальные токи КЗ](https://www.electrical-installation.org/enwiki/Calculation_of_minimum_levels_of_short-circuit_current). Чувствительность к малому току, разделение защит для ПЧ, тепловая проверка кабеля.
- S3 — [Schneider Electric: MicroLogic X, селективность](https://productinfo.se.com/micrologicxuserguide/viewer?docidentity=D-SE-0060785&extension=xml&lang=en). Условия селективности и связи с функциями расцепителя. Конкретные настройки только по руководству выбранной модели.
- S4 — [Schneider Electric: асинхронные двигатели](https://www.electrical-installation.org/enwiki/Induction_motors). Пуск, перегрузка, защита от КЗ и координация пускателей.
- S5 — [Schneider Electric: тепловая стойкость кабелей при КЗ](https://www.electrical-installation.org/enwiki/Verification_of_the_withstand_capabilities_of_cables_under_short-circuit_conditions) и [основы защиты от сверхтоков](https://www.electrical-installation.org/enwiki/Overcurrent_protection_principles). Применимость I²t ≤ k²S², перегрузка и допустимый ток.
- S6 — [Schneider Electric: Selectivity, Cascading and Coordination Guide 2026](https://www.se.com/uk/en/download/document/LVPED318033EN/). Таблицы точных комбинаций, пределы селективности, каскадирование и моторные цепи.
- A1 — [ABB: способы обеспечения селективности](https://new.abb.com/low-voltage/el/our-solutions/selectivity/basic-concepts/selectivity-techniques). Ток, время, энергия, зонное согласование и проверка характеристик.

Серия не задаёт обязательные нормативные коэффициенты чувствительности, фиксированные интервалы или универсальную политику АПВ. Для ОЗЗ отдельно рассматриваются изолированная, компенсированная и резистивно заземлённая нейтрали. Для 0,4 кВ расчётные примеры используют TN-S; перенос в TT/IT требует отдельного обоснования.
