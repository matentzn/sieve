## Add your own just recipes here. This is imported by the main justfile.

# ============== Evidence-model transforms (linkml-map) ==============
# Demonstrates the minimal microschema: a DisMech record is transformed into the
# minimal model, then lifted into the full sieve model. See docs/monarch_evidence.md.

_transform_build := "transform/build"

# Transform a DisMech pathophysiology assertion into the minimal microschema, then validate.
transform-dismech:
    mkdir -p {{_transform_build}}
    uv run linkml-map map-data \
        -T transform/dismech_to_minimal.transform.yaml \
        -s transform/dismech_source.yaml --source-type Pathophysiology \
        transform/dismech_fanconi_input.yaml \
        -o {{_transform_build}}/fanconi_minimal.yaml
    uv run linkml-validate -s schema/minimal.yaml -C EvidencedClaim {{_transform_build}}/fanconi_minimal.yaml
    @echo "OK: transform/build/fanconi_minimal.yaml validates against schema/minimal.yaml"

# Lift the minimal record into the full sieve EvidencePacket model, then validate.
transform-minimal-to-sieve: transform-dismech
    uv run linkml-map map-data --unrestricted-eval \
        -T transform/minimal_to_sieve.transform.yaml \
        -s schema/minimal.yaml --source-type EvidencedClaim \
        {{_transform_build}}/fanconi_minimal.yaml \
        -o {{_transform_build}}/fanconi_sieve.yaml
    uv run linkml-validate -s schema/sieve.yaml -C EvidencePacket {{_transform_build}}/fanconi_sieve.yaml
    @echo "OK: transform/build/fanconi_sieve.yaml validates against schema/sieve.yaml"

# Run the whole DisMech -> minimal -> sieve pipeline end to end.
transform-all: transform-minimal-to-sieve
    @echo "Pipeline complete: DisMech -> minimal -> sieve (both outputs validated)."


# ============== Schema reference docs (linkml gen-doc) ==============
# Generates the per-class/slot markdown reference the "Schema Reference" nav section
# serves. Output (docs/elements/) is gitignored and regenerated on build/deploy.

# Generate the LinkML schema reference into docs/elements/.
gen-docs:
    uv run gen-doc -d docs/elements schema/sieve.yaml
    @echo "Schema reference generated in docs/elements/ (from schema/sieve.yaml)"

# Serve the docs locally with a freshly generated schema reference.
serve-docs: gen-docs
    uv run mkdocs serve
