DELETE FROM employees;

INSERT INTO employees (employee_id, department_id) VALUES
-- IT
('@Ivan_IT', (SELECT id FROM departments WHERE name = 'IT')),
('@Petr_IT', (SELECT id FROM departments WHERE name = 'IT')),
-- Бухгалтерия
('@Oksana_Buh', (SELECT id FROM departments WHERE name = 'Бухгалтерия')),
('@Elena_Buh', (SELECT id FROM departments WHERE name = 'Бухгалтерия')),
-- Маркетинг
('@Maria_Mark', (SELECT id FROM departments WHERE name = 'Маркетинг')),
('@Sergey_Mark', (SELECT id FROM departments WHERE name = 'Маркетинг')),
-- Отдел кадров
('@Anna_HR', (SELECT id FROM departments WHERE name = 'Отдел кадров')),
('@Tatyana_HR', (SELECT id FROM departments WHERE name = 'Отдел кадров')),
-- Логистика
('@Dmitry_Log', (SELECT id FROM departments WHERE name = 'Логистика')),
('@Alex_Log', (SELECT id FROM departments WHERE name = 'Логистика')),
-- Юридический отдел
('@Olga_Law', (SELECT id FROM departments WHERE name = 'Юридический отдел')),
('@Igor_Law', (SELECT id FROM departments WHERE name = 'Юридический отдел')),
-- Отдел продаж
('@Natalia_Sales', (SELECT id FROM departments WHERE name = 'Отдел продаж')),
('@Andrey_Sales', (SELECT id FROM departments WHERE name = 'Отдел продаж')),
-- Техническая поддержка
('@Viktor_Support', (SELECT id FROM departments WHERE name = 'Техническая поддержка')),
('@Yulia_Support', (SELECT id FROM departments WHERE name = 'Техническая поддержка')),
-- Аналитический отдел
('@Mikhail_Analytic', (SELECT id FROM departments WHERE name = 'Аналитический отдел')),
('@Ksenia_Analytic', (SELECT id FROM departments WHERE name = 'Аналитический отдел')),
-- Отдел разработки
('@Nikolay_Dev', (SELECT id FROM departments WHERE name = 'Отдел разработки')),
('@Svetlana_Dev', (SELECT id FROM departments WHERE name = 'Отдел разработки'));