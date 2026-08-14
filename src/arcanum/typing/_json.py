from typing import Any

type JSONScalar = str | float | int | bool | None
type JSONArray = list[JSONScalar | list[Any] | dict[str, Any]]
type JSONObject = dict[str, JSONScalar | list[Any] | dict[str, Any]]
type JSONScalarArray = list[JSONScalar]
type JSONScalarObject = dict[str, JSONScalar]
