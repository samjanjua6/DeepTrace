# Debug & Ad-hoc Inspection Utilities

This directory holds developer diagnostic and database inspection scripts.

> [!NOTE]
> These scripts are gitignored to avoid repo clutter. Run them from the project root using your Python virtual environment.

## Categories

### Database & User Diagnostics
* `check_db.py`: Verifies database connectivity, tenant organization contexts, and pipeline run durations.
* `check_risks.py`: Checks risk score distributions and calculations.
* `check_users_mfa.py`: Inspects user MFA status and credentials.
* `check_real_emojis.py` / `check_zero_emoji.py`: Verifies emoji and Unicode rendering in logs and database entries.

### Forensic & CMFD Testing
* `test_cmfd_filter.py`: Tests copy-move forgery detection filters.
* `test_full_cmfd.py`: Full end-to-end execution of copy-move detector.
* `test_mask_cmfd.py`: Verifies mask generation for image tampering.
* `test_meezan_profile.py`: Verifies Meezan Bank statement profile extraction.

### Investigation & Pipeline Inspection
* `find_case.py` / `find_exact_evidence.py` / `find_ts_div.py`: Queries specific cases and evidence records.
* `inspect_all_invs.py` / `inspect_top_invs.py` / `inspect_top3.py` / `inspect_inv_case.py`: Inspects investigation statuses.
* `inspect_pdf_deep.py` / `inspect_spans.py` / `inspect_header_spans.py` / `inspect_fonts.py` / `inspect_columns.py` / `inspect_last_page.py`: Low-level PDF span, font, and text extraction checks.
* `inspect_pipeline_runs.py` / `rerun_pipeline_docket40.py` / `test_pipeline_findings.py`: Inspects or reruns background Celery pipeline stages.
* `test_alias.py`: Tests alias resolution.
* `test_live_dashboard.py`: Tests analytics and live dashboard data generation.
