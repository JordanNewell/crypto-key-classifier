## Summary

<!-- One or two sentences. What does this PR change and why? -->

## Type

<!-- Check one -->

- [ ] Bug fix (non-breaking)
- [ ] New validator / chain support
- [ ] Improvement to existing validator (broader recovery, better masking)
- [ ] Documentation
- [ ] Refactor (no behavior change)
- [ ] Breaking change

## Checklist

- [ ] `ruff check .` clean
- [ ] `pyright` clean (strict mode)
- [ ] `pytest` green (239+ tests)
- [ ] If new validator: added public test vectors under `tests/fixtures/` (no real mainnet keys)
- [ ] If new validator: added a property test under `tests/fuzz/`
- [ ] README updated (validator table, examples, or changelog reference)
- [ ] Commits signed
- [ ] No AI-attribution trailers (`Co-Authored-By: Claude`, etc.)

## Test plan

<!-- How did you verify this works? Paste the CLI invocations + observed output. -->

```
$ classify-key ...
```

## Security considerations

<!-- If this touches input handling, masking, file I/O, or the repair pipeline,
note any new attack surface and how it was verified safe. -->
