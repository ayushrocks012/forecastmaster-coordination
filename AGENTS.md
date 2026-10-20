# ForecastMaster coordination repository

This is the separate office-laptop script and feedback handoff. Keep changes here; the Smart Demand Manager application checkout is outside this task's requested scope.

Use `main`. Pull with `--ff-only` before starting a handoff and commit/push the completed handoff before the other laptop receives it. Preserve local edits if a conflict occurs; do not reset or force-push to clear it.

`START-HERE.md` owns office SSH and VS Code setup. `feedback/STATUS.md` distinguishes confirmed company results from pending installation or runtime checks. The current script versions are notebook R05.3 and function source R05.2.

`handoff/` contains byte-preserved, selected script packages prepared in the preceding chat. `HANDOFF-MANIFEST.json` records their initial file hashes. Run `python tools/verify_handoff.py` to check this receiving copy. Changes to handoff code require updating the relevant tests and manifest together and explaining the change to the receiving operator.

The notebook and Functions files are copy/paste inputs for Fabric; merely committing or cloning them does not install or run anything in Fabric. Keep local tests, company installation, company runtime results, and report publication as separate facts.

Keep SSH credentials outside the repository. Screenshots and run outputs belong in `feedback/`; this repository is public.
