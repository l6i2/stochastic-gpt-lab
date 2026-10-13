# Controller verification status

2026-10-13: C1 verified against running XM, unique Data Folder
20C285FE08971A9A2E814AAC44AFC9D2. Read-only API reports connected DEMO,
US30Cash available. DEMO executor is NOT_IMPLEMENTED and disabled.
Two environment unit tests pass. CIM discovery timed out; psutil discovery works.

C2 PASS: active dedicated source and includes match repository working files.
MetaEditor compiled with 0 errors and 0 warnings; EX5 and SHA-256 recorded.

C3 FAIL: two documented /config launches (UTF-16 and ASCII) returned exit 0
without fresh tester logs, tester agent process, or nonce-named output artifacts.
The original XM PID 7880 remained active. This is consistent with an existing
instance ignoring startup configuration; causation needs a clean-start check.
No terminal process was terminated. No mouse/keyboard automation was used.

C4 and C5: source implemented, end-to-end acceptance BLOCKED by C3. The checkpoint
contains PENDING blocks 2023-12-20..31, 2024, 2025, and 2026-01-01..03-19.
History refuses execution without a validated smoke run and causal acceptance.
Eight controller tests pass. Existing profile future-perturbation test passes.
This proves the reference causal profile only; whole snapshot producer invariance
is NOT_VERIFIED and is a second acceptance blocker. Native g++ tests are unavailable.
No CONTROLLER_C1_C5_COMPLETE checkpoint was written.

MANUAL_ACTION: close XM normally once it is idle, then launch it with the saved
recovery.ini in run r20261013T112613_6b130b68. This is a clean-start diagnostic,
not an accepted smoke result. Do not select a different account.

After tester completion, from this worktree use:
`.venv\Scripts\python.exe -m controller.controller resume --run-id r20261013T112613_6b130b68`.
It verifies the source/binary and nonce, then runs split-aware validators. It will
not approve causality automatically or unlock history without the missing proof.

FINAL_TEST remains locked; live trading is false. DEMO_EXECUTOR=NOT_IMPLEMENTED.
