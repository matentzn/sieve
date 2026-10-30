# Examples of using sieve

This folder holds no data of its own. Example packets in the SIEVE profile shape live
elsewhere in the repository:

- [tests/data/profile/valid/](../tests/data/profile/valid/): one packet each for C003
  (synonym, policy acceptance), C005 (negative subclass, disputing evidence), C006
  (mapping, batch sign-off) and C007 (gene-disease, AI-extracted passage, panel
  sign-off).
- [tests/data/profile/registry.yaml](../tests/data/profile/registry.yaml): the
  `SieveRegistry` those packets refer to (resources, releases, agents, methods, rules,
  policies, batches).
- [inbox/examples/](../inbox/examples/): further packets, for ingest once the
  application layer is migrated.
- [monarch_evidence/examples/](../monarch_evidence/examples/): real DisMech, MeDIC and
  mondo-ai records with their SIEVE rendering, or the fragments that fit where the
  claim lies outside the profile.

Validate one with:

```bash
uv run linkml-validate -s schema/sieve.yaml -C EvidencePacket <file>
```

linkml-validate needs dates quoted in YAML; the test fixtures leave them unquoted and
are validated by the tests with dates kept as strings. See `docs/data-model.md`.
