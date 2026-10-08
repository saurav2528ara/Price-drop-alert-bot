---
name: Python dependency inference
description: Replit package installation can infer an unrelated telegram distribution from imports.
---

The package installer may automatically add `telegram` alongside `python-telegram-bot`. The imported `telegram` namespace should come from `python-telegram-bot`, not the unrelated `telegram` distribution.

**Why:** During setup, automatic import inference installed both distributions. Uninstalling the unrelated distribution removed shared namespace files and broke imports from the intended library.

**How to apply:** Preserve the original dependency list, check imports after package operations, and ensure the intended library is reinstalled if removal of the unrelated distribution damages its namespace. Package tokens reject pip flags such as `--force-reinstall`.
