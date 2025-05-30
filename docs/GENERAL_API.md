# Langs2Brain General API Documentation

Welcome to the Langs2Brain API!

## Contents

- [Authentication](#authentication)
- [API Usage](#api-usage)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Available Models](#available-models)
    - [Word](WORD_API.md)
    - [WordTranslation](WORDTRANSLATION_API.md)
- [OpenAPI/Swagger](#openapiswagger)
- [Contact](#contact)

---

## Authentication

> **Currently, the API does not require authentication.**
> In the future, token authentication (JWT or DRF token) may be enabled for user‑specific features.

---

## API Usage

- All endpoints accept and return JSON.
- Use standard REST verbs: `GET`, `POST`, `PUT`, `DELETE`.
- All list endpoints support pagination if enabled.

---

## Response Format

- Successful requests return `200 OK` (list/get), `201 Created` (create), or `204 No Content` (delete).
- Errors return JSON with an appropriate status code (`400`, `404`, etc.).

Example error response:
```json
{
  "detail": "Not found."
}
```

---

## Error Handling

- **Unique constraints** (e.g., duplicate word‑language or translation pair) return `400 Bad Request` with a message.
- Invalid fields return `400` and a detailed list of errors.

---

## Available Models

- [Word](WORD_API.md) — individual words with metadata & notes.
- [WordTranslation](WORDTRANSLATION_API.md) — translation pairs with type & confidence.

---

## OpenAPI/Swagger

If `drf-spectacular` or `drf-yasg` is installed, visit `/api/schema/` or `/swagger/` for a live schema and playground.

---

## Contact

For support or questions, contact the Langs2Brain project team.

---
