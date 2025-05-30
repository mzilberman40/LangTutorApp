# Word API Documentation

## Endpoints

### List all words  
**GET** `/api/words/`

### Create word(s)  
**POST** `/api/words/`  
• single JSON object or array for bulk

### Retrieve word  
**GET** `/api/words/{id}/`

### Update word  
**PUT** `/api/words/{id}/`

### Delete word  
**DELETE** `/api/words/{id}/`

---

## Fields

| Field | Type | Notes |
|-------|------|-------|
| id | int | auto |
| word | string | required |
| language | string | BCP‑47 (e.g. `en‑GB`) |
| status | string | `learning` / `known` / `to_review` |
| notes | string | optional |
| part_of_speech | string | noun/verb/… |
| pronunciation | string | IPA, optional |
| date_added | datetime | read‑only |
| last_reviewed | datetime | optional |

**Uniqueness:** (`word`, `language`) must be unique.
