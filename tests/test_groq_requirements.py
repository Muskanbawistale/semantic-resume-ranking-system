from src.llm.groq_requirements import _make_schema_strict
from src.domain.models import HiringRequirements


def test_groq_schema_marks_every_object_strict_and_required():
    schema = HiringRequirements.model_json_schema()
    _make_schema_strict(schema)

    objects = [schema]
    objects.extend(
        definition
        for definition in schema.get("$defs", {}).values()
        if definition.get("type") == "object"
    )

    assert objects
    for object_schema in objects:
        assert object_schema["additionalProperties"] is False
        assert set(object_schema["required"]) == set(object_schema["properties"])
