<!-- Thanks for contributing to Keel. Keep the description short and concrete. -->

## What and why

<!-- What does this change, and why? Link any related issue (e.g. Closes #12). -->

## Type

- [ ] Catalog: new or edited threat / mitigation
- [ ] Catalog: correction to existing content
- [ ] Code / tooling
- [ ] Docs

## Checklist

- [ ] Every commit is signed off: `git commit -s` ([DCO](https://github.com/roselis-lab/keel/blob/main/CONTRIBUTING.md#sign-off-your-commits-dco))
- [ ] `uv run ruff check .` passes
- [ ] `uv run pytest` passes
- [ ] For catalog changes: I edited `catalog/*.yaml` and ran `uv run keel validate`
- [ ] For catalog changes: content follows the style guide bar (impact-centric threat, `reachability` carve-outs, mitigation card with a `mitigation_class`)
- [ ] This belongs in the shared catalog (a general pattern), not org-specific state that should live in a fork
