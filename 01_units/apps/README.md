Shared utilities that are reused across multiple pipeline stages live here.

Current shared modules:

- `lms_text_cleaning.py`: reusable LMS response cleaning helpers. It normalizes HTML-quoted CSV payloads, strips LMS HTML markup to plain text, repairs common emojibake patterns, normalizes non-breaking spaces, and provides helpers such as `clean_lms_response_text(...)` and `is_lms_response_column(...)`.

Because the repository root folder is named `01_units`, these modules are consumed by adding the `01_units/apps` directory to `sys.path` from calling scripts rather than by importing `01_units` as a Python package.
