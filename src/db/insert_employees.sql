DELETE FROM employees;

INSERT INTO employees (employee_id, department_id, full_name, department_name) VALUES
-- IT
('@Ivan_IT', (SELECT id FROM departments WHERE name = 'IT'), 'Иван Иванов', 'IT'),
('@Petr_IT', (SELECT id FROM departments WHERE name = 'IT'), 'Пётр Петров', 'IT'),
-- Бухгалтерия
('@Oksana_Buh', (SELECT id FROM departments WHERE name = 'Бухгалтерия'), 'Оксана Бухарева', 'Бухгалтерия'),
('@Elena_Buh', (SELECT id FROM departments WHERE name = 'Бухгалтерия'), 'Елена Бухарева', 'Бухгалтерия'),
-- Маркетинг
('@Maria_Mark', (SELECT id FROM departments WHERE name = 'Маркетинг'), 'Мария Маркетова', 'Маркетинг'),
('@Sergey_Mark', (SELECT id FROM departments WHERE name = 'Маркетинг'), 'Сергей Маркетов', 'Маркетинг'),
-- Отдел кадров
('@Anna_HR', (SELECT id FROM departments WHERE name = 'Отдел кадров'), 'Анна Кадрова', 'Отдел кадров'),
('@Tatyana_HR', (SELECT id FROM departments WHERE name = 'Отдел кадров'), 'Татьяна Кадрова', 'Отдел кадров'),
-- Логистика
('@Dmitry_Log', (SELECT id FROM departments WHERE name = 'Логистика'), 'Дмитрий Логистов', 'Логистика'),
('@Alex_Log', (SELECT id FROM departments WHERE name = 'Логистика'), 'Алекс Логистов', 'Логистика'),
-- Юридический отдел
('@Olga_Law', (SELECT id FROM departments WHERE name = 'Юридический отдел'), 'Ольга Юристова', 'Юридический отдел'),
('@Igor_Law', (SELECT id FROM departments WHERE name = 'Юридический отдел'), 'Игорь Юристов', 'Юридический отдел'),
-- Отдел продаж
('@Natalia_Sales', (SELECT id FROM departments WHERE name = 'Отдел продаж'), 'Наталья Продажнова', 'Отдел продаж'),
('@Andrey_Sales', (SELECT id FROM departments WHERE name = 'Отдел продаж'), 'Андрей Продажнов', 'Отдел продаж'),
-- Техническая поддержка
('@Viktor_Support', (SELECT id FROM departments WHERE name = 'Техническая поддержка'), 'Виктор Поддержкин', 'Техническая поддержка'),
('@Yulia_Support', (SELECT id FROM departments WHERE name = 'Техническая поддержка'), 'Юлия Поддержкина', 'Техническая поддержка'),
-- Аналитический отдел
('@Mikhail_Analytic', (SELECT id FROM departments WHERE name = 'Аналитический отдел'), 'Михаил Аналитиков', 'Аналитический отдел'),
('@Ksenia_Analytic', (SELECT id FROM departments WHERE name = 'Аналитический отдел'), 'Ксения Аналитикова', 'Аналитический отдел'),
-- Отдел разработки
('@Nikolay_Dev', (SELECT id FROM departments WHERE name = 'Отдел разработки'), 'Николай Разработкин', 'Отдел разработки'),
('@Svetlana_Dev', (SELECT id FROM departments WHERE name = 'Отдел разработки'), 'Светлана Разработкина', 'Отдел разработки');