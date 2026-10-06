from basira.api.schemas import (
    GeneralMaterialResponse,
    QueryResponse,
)


def test_query_response_exposes_general_material() -> None:
    schema = QueryResponse.model_json_schema()

    assert "general_material" in schema["properties"]


def test_general_material_has_no_evidence_field() -> None:
    schema = GeneralMaterialResponse.model_json_schema()

    properties = schema["properties"]

    assert "materials" in properties

    # Important anti-laundering boundary.
    assert "evidence" not in properties
    assert "citations" not in properties
