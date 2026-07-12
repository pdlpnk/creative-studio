# Creative Bible v1

## Назначение

Creative Bible — единый источник знаний для всех рекламных креативов проекта. Каждая строка в базе представляет собой один Creative Concept и хранит его содержание, производственный статус и связи с сопутствующими артефактами.

Версия 1 охватывает только:

- статические изображения;
- формат `1080x1080`.

Видео, сторис, рилсы и любые другие форматы в Creative Bible v1 не учитываются.

## Основной лист Google Sheets

Название листа: `03_Creative_Library`.

Каждая строка листа соответствует одному Creative Concept. Первая строка содержит заголовки колонок в порядке, указанном ниже.

## Структура

| Column | Type | Required | Description |
|---|---|---|---|
| `concept_id` | text | yes | Уникальный ID концепта в формате `CC-0001`. |
| `name` | text | yes | Краткое название концепта. |
| `geo` | enum | yes | `TR` / `AZ`. |
| `funnel` | enum | yes | `registration` / `lead`. |
| `objective` | enum | yes | `CTR` / `Registration Rate` / `Lead Quality`. |
| `theme` | text | yes | Основная идея. |
| `style` | text | yes | Например: `Minimal`, `Premium`, `Summer`, `Luxury`, `Crypto`, `UI`. |
| `season` | enum | yes | `Spring` / `Summer` / `Autumn` / `Winter` / `Evergreen`. |
| `language` | enum | yes | `TR` / `AZ`. |
| `format` | enum | yes | Только `1080x1080`. |
| `headline` | text | no | Главный заголовок. |
| `supporting_copy` | text | no | Дополнительный текст. |
| `cta` | text | no | Призыв к действию (CTA). |
| `visual_brief` | long text | yes | Полное описание композиции. |
| `hypothesis` | long text | yes | Что именно проверяет этот креатив. |
| `status` | enum | yes | `idea` / `approved` / `production` / `testing` / `winner` / `loser` / `archived`. |
| `parent_id` | text | no | ID родительского концепта. |
| `variant` | text | no | Обозначение варианта, например `V01`. |
| `asset_url` | url | no | Ссылка на изображение. |
| `prompt_id` | text | no | ID связанного промпта. |
| `created_at` | datetime | yes | Дата и время создания. |
| `created_by` | text | yes | `Human` / `ChatGPT` / `Codex`. |
| `notes` | long text | no | Комментарии. |

## Validation

- `concept_id` обязателен и уникален для каждой строки.
- `format` всегда равен `1080x1080`.
- Статусы `winner` и `loser` допустимы только после этапа `testing`.
- `hypothesis` обязательна.
- `visual_brief` обязателен.
- Переход в статус `approved` невозможен без заполненного `visual_brief`.
- Нельзя использовать неподтверждённые обещания, гарантии выигрыша, ложные отзывы и другой вводящий в заблуждение рекламный текст.
- Значения enum-полей должны выбираться только из списков, заданных в разделе «Структура».

## ID

### Concept

```text
CC-0001
```

### Variant

```text
CC-0001-V01
```

В строке варианта `parent_id` содержит ID родительского концепта (`CC-0001`), а `variant` — обозначение варианта (`V01`).

### Prompt

```text
PRM-0001
```

## Status Flow

```text
idea
  ↓
approved
  ↓
production
  ↓
testing
  ↓
winner / loser
  ↓
archived
```

Статус отражает текущий этап жизненного цикла Creative Concept. Переход к `archived` завершает активную работу с концептом, но не удаляет его из базы знаний.

## Требования к Google Sheets

Лист `03_Creative_Library` должен быть настроен следующим образом:

- первая строка закреплена;
- для всего диапазона данных включены фильтры;
- для enum-полей настроены dropdown-списки с допустимыми значениями из раздела «Структура»;
- колонки `concept_id` и `created_at` защищены от случайного редактирования;
- поле `format` автоматически заполняется значением `1080x1080`;
- создание и использование любых других форматов запрещено в рамках Creative Bible v1.

Эта спецификация описывает целевую структуру листа, но не реализует подключение или автоматизацию Google Sheets.
