# LangTutorApp – Coding Guidelines (v1.0)

These rules are **mandatory** for every contributor.  
Stick to them and code‑review will focus on logic, not formatting.

---

## 1. Repository

* **Origin:** <https://github.com/mzilberman40/LangTutorApp.git>
* **Default branch:** `main`
* Push only via pull‑request; never commit directly to `main`.

---

## 2. Development Environment

| Item | Requirement |
|------|-------------|
| IDE  | **PyCharm Pro 2025.1** (or later) |
| Python | 3.12 (use `pyenv` or `asdf` if needed) |
| Virtual‑env | One per project (`.venv/`) |
| OS | Windows 11, macOS 13+ or Linux |

---

## 3. Workflow

1. Create a short‑lived *feature branch* off `main`.
2. **TDD**: write a failing test → implement code → make tests pass.
3. Ensure test‑suite passes: `pytest -q`.
4. Format + sort imports (Black + isort) – see §4.
5. Commit with a concise message; push and open a PR.

---

## 4. Coding Style & Formatting  ✔ (item 6)

| Tool | Purpose | Command |
|------|---------|---------|
| **Black** | Enforce PEP 8 layout (88‑char lines) | `black .` |
| **isort** | Sort & group imports (`--profile black`) | `isort .` |

*PyCharm set‑up:*  
`Settings → Tools → Black` → enable **on save**.  
Install the *isort* plugin → enable **on save**.

---

## 5. Docstrings & API documentation  ✔ (item 16)

* Use the **Google** docstring style.
* Every **public function, class and method** must have a docstring.
* Sections order: `Args`, `Returns`, `Raises`, `Example`.
* Example:

```python
def slugify(text: str) -> str:
    """Convert text to a URL‑friendly slug.

    Args:
        text: Raw input string from the user.

    Returns:
        A lowercase string containing letters, digits and hyphens only.

    Raises:
        ValueError: If *text* is empty.
    """
```

Sphinx + `mkdocstrings` will render these automatically.

---

## 6. Logging  ✔ (item 17)

| Level | When to use |
|-------|-------------|
| `DEBUG` | Verbose, step‑by‑step info useful during dev |
| `INFO`  | High‑level application flow |
| `WARNING` | Recoverable problems, retries |
| `ERROR` | Unhandled exceptions that don’t crash the service |
| `CRITICAL` | The service is unusable |

* Use the root logger from `logging.getLogger(__name__)`.  
* Never `print()`.  
* In production, emit **JSON** logs via `logging_config.py`.

---

## 7. Secrets & configuration  ✔ (item 19)

* **Never** commit credentials, API keys or `.env` files.
* Configuration hierarchy (highest priority first):
  1. Environment variables
  2. `.env` file **ignored** by Git
  3. Default values in `settings.py`
* Use `python-dotenv` for local development.

---

## 8. Commit & PR checklist

- [ ] Tests added or updated (TDD).
- [ ] `pytest -q` passes.
- [ ] `black . && isort .` produce no changes.
- [ ] No TODOs or debug prints remain.
- [ ] Docstrings written/updated.
- [ ] No secrets in diff.
- [ ] Someone else has reviewed the PR.

---

_Last updated: 2025-04-23_
