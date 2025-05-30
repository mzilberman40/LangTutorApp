# WordTranslation API Documentation

## Endpoints

### List translations  
**GET** `/api/word-translations/`

### Create translation  
**POST** `/api/word-translations/`

### Retrieve translation  
**GET** `/api/word-translations/{id}/`

### Delete translation  
**DELETE** `/api/word-translations/{id}/`

---

## Fields

| Field | Type | Notes |
|-------|------|-------|
| id | int | auto |
| source_word | int | FK → Word |
| target_word | int | FK → Word |
| translation_type | string | `manual` / `ai` / `user` / `imported` |
| confidence | float | 0‑1, optional |

**Uniqueness:** (`source_word`, `target_word`) pair must be unique.
