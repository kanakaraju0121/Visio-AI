# Contributing

1. Create a branch for each focused change.
2. Keep hardware-specific assumptions configurable and document the exact board / OS used.
3. Never commit secrets, personal face data, runtime captures or private TLS keys.
4. Run syntax checks before opening a pull request:
   ```bash
   python -m compileall -q .
   ```
5. For hardware-dependent changes, include the test setup and exact observed result. Do not report unperformed tests as passing.

Please describe what was changed, why it was changed, and how it was tested.
