These research documents (A1–A8) proposed a runtime-JS widget architecture (Lit 3 + Motion One + uPlot + Graphviz + ELK.js) for Scriba. They were REJECTED in Pivot #2 (2026-04-09) because runtime JS breaks portability to Codeforces, AtCoder, GitHub, email, PDF, and other platforms where CP editorials live.

Several IDEAS from these documents were cherry-picked and reimplemented as pure-Python compile-time features in `docs/scriba/extensions/` and `docs/scriba/primitives/`. See `docs/scriba/00-ARCHITECTURE-DECISION-2026-04-09.md` for the full decision rationale.

Do not cite these documents as current spec. They are preserved only for decision trail.
