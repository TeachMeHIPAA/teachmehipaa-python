"""Generate the resource and model layer from the vendored SDK IR.

    uv run python scripts/generate.py          # rewrite the generated files
    uv run python scripts/generate.py --check  # fail if they are stale

Reads only `openapi/sdk-ir.json` (validated against `sdk-ir.schema.json`) and
writes `src/teachmehipaa/types/` and `src/teachmehipaa/resources/`. The output
is ruff-formatted and byte-for-byte deterministic. Any IR shape this
generator has no rule for stops it with an error rather than guessing.
"""

from __future__ import annotations

import argparse
import difflib
import json
import keyword
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import pydantic
from pydantic.alias_generators import to_camel

ROOT = Path(__file__).resolve().parent.parent
IR_PATH = ROOT / "openapi" / "sdk-ir.json"
SCHEMA_PATH = ROOT / "openapi" / "sdk-ir.schema.json"
PACKAGE = ROOT / "src" / "teachmehipaa"
GENERATED_DIRS = ("types", "resources")
EXTENSIONS = PACKAGE / "_extensions"

# Top-level resources with hand-written methods, by IR path. The generator
# names their classes `<Name>Base` and `Async<Name>Base`;
# `_extensions/<module>.py` subclasses them under the plain names, and the
# client exposes those subclasses.
EXTENDED_RESOURCES = frozenset({"events"})

BANNER = (
    "# Generated from openapi/sdk-ir.json — do not edit.\n"
    "# Regenerate with `uv run python scripts/generate.py`.\n"
)
LINE_LENGTH = 88
# Mirrors `_core._unions.UNKNOWN_VARIANT`. The generator can't import the
# package: that would import the generated code it is about to replace.
UNKNOWN_VARIANT = "<unknown>"

Json = Any


class GeneratorError(Exception):
    """The IR has a shape this generator has no rule for."""


# --- naming ---------------------------------------------------------------


def snake(name: str) -> str:
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return name.lower()


def camel(name: str) -> str:
    """Mirrors `_core._request.camel`, which sends TypedDict keys."""
    first, *rest = name.split("_")
    return first + "".join(part[:1].upper() + part[1:] for part in rest)


def pascal(name: str) -> str:
    return name[:1].upper() + name[1:]


def identifier(name: str) -> str:
    """A Python identifier for an IR name: snake_case, with PEP 8's trailing
    underscore when it would collide with a keyword."""
    python_name = snake(name)
    return python_name + "_" if keyword.iskeyword(python_name) else python_name


def constant(name: str) -> str:
    return snake(name).upper()


# --- docstrings -----------------------------------------------------------


def docstring(paragraphs: Iterable[str | None], indent: int) -> list[str]:
    """A triple-quoted docstring wrapped to the line length, as lines.

    Each line of a paragraph wraps on its own, so lists stay lists; a list
    item or an `Args:` entry continues one level deeper than it starts.
    """
    width = LINE_LENGTH - indent
    texts = [
        p.replace("\\", "\\\\").replace('"""', '\\"\\"\\"') for p in paragraphs if p
    ]
    if not texts:
        return []
    one_line = f'"""{texts[0]}"""'
    if len(texts) == 1 and "\n" not in texts[0] and len(one_line) <= width:
        return [" " * indent + one_line]
    body: list[str] = []
    for text in texts:
        if body:
            body.append("")
        for line in text.splitlines():
            stripped = line.lstrip()
            hang = " " * (len(line) - len(stripped))
            if stripped.startswith("- "):
                hang += "  "
            elif hang and re.match(r"\w+: ", stripped):
                hang += "    "
            body += textwrap.wrap(
                line,
                width=width,
                # The opening quotes share the first line.
                initial_indent='"""' if not body else "",
                subsequent_indent=hang,
                break_long_words=False,
                break_on_hyphens=False,
            ) or [""]
    pad = " " * indent
    return [pad + line if line else "" for line in body] + [f'{pad}"""']


# --- the IR model ----------------------------------------------------------


@dataclass
class Ir:
    raw: Json
    types: dict[str, Json] = field(init=False)
    methods: list[tuple[tuple[str, ...], Json]] = field(init=False)

    def __post_init__(self) -> None:
        self.types = {t["name"]: t for t in self.raw["types"]}
        self.methods = [
            (tuple(resource["path"]), method)
            for resource in self.raw["resources"]
            for method in resource["methods"]
        ]

    @property
    def event_envelope(self) -> str:
        return str(self.raw["events"]["envelope"])

    @property
    def unknown_event(self) -> str:
        return str(self.raw["events"]["unknownEvent"])

    def kind(self, name: str) -> str:
        return str(self.types[name]["kind"])

    def fallback_of(self, union: Json) -> str | None:
        """The model an unknown variant of `union` parses as."""
        discriminator = union["discriminator"]
        if discriminator["kind"] == "presence":
            fallback = discriminator["fallback"]
            return None if fallback is None else str(fallback)
        if union["name"] == self.event_envelope:
            return self.unknown_event
        return f"Unknown{union['name']}"

    def page_types(self) -> dict[str, Json]:
        """Page model name -> its item type, from every page response."""
        pages: dict[str, Json] = {}
        for _, method in self.methods:
            if method["response"]["kind"] == "page":
                pages[method["response"]["type"]["name"]] = method["pagination"][
                    "itemType"
                ]
        return pages


def refs(type_ref: Json) -> Iterator[str]:
    kind = type_ref["kind"]
    if kind == "ref":
        yield type_ref["name"]
    elif kind == "array":
        yield from refs(type_ref["items"])
    elif kind == "map":
        yield from refs(type_ref["values"])


def variants(ir: Ir, union: Json, *, unknown: bool) -> list[str]:
    """A union's variant models, with a property union's fallback for
    unknown tags when `unknown` is set. Requests never send unknown tags."""
    names = list(dict.fromkeys(union["discriminator"]["mapping"].values()))
    fallback = ir.fallback_of(union)
    is_presence = union["discriminator"]["kind"] == "presence"
    if fallback is not None and (unknown or is_presence):
        names.append(fallback)
    return names


def dependencies(ir: Ir, ir_type: Json, *, unknown: bool = True) -> set[str]:
    if ir_type["kind"] == "object":
        return {name for f in ir_type["fields"] for name in refs(f["type"])}
    if ir_type["kind"] == "union":
        return set(variants(ir, ir_type, unknown=unknown))
    return set()


def topological(names: Iterable[str], deps: Mapping[str, set[str]]) -> list[str]:
    """`names` ordered so each comes after what it depends on; ties sort by
    name, which keeps the output stable."""
    ordered: list[str] = []
    state: dict[str, str] = {}

    def visit(name: str) -> None:
        if state.get(name) == "done":
            return
        if state.get(name) == "visiting":
            raise GeneratorError(f"reference cycle through {name}")
        state[name] = "visiting"
        for dependency in sorted(deps.get(name, set())):
            if dependency in deps:
                visit(dependency)
        state[name] = "done"
        ordered.append(name)

    for name in sorted(names):
        visit(name)
    return ordered


# --- models ----------------------------------------------------------------

PRIMITIVES = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "dateTime": "datetime",
    "binary": "bytes",
    "json": "Any",
}


def model_type(type_ref: Json) -> str:
    kind = type_ref["kind"]
    if kind == "primitive":
        if type_ref["type"] not in PRIMITIVES:
            raise GeneratorError(f"no model type for primitive {type_ref['type']}")
        return PRIMITIVES[type_ref["type"]]
    if kind == "ref":
        return str(type_ref["name"])
    if kind == "array":
        return f"list[{model_type(type_ref['items'])}]"
    return f"dict[str, {model_type(type_ref['values'])}]"


def field_name(wire_name: str) -> str:
    """The attribute name of a response field."""
    name = snake(wire_name)
    if keyword.iskeyword(name) or hasattr(pydantic.BaseModel, name):
        name += "_"
    return name


def model_field(field_: Json) -> list[str]:
    name = field_name(field_["name"])
    annotation = model_type(field_["type"])
    if field_["nullable"] and annotation != "Any":
        annotation += " | None"
    arguments = []
    if not field_["required"]:
        arguments.append("default=None")
        if " | None" not in annotation and annotation != "Any":
            annotation += " | None"
    if to_camel(name) != field_["name"]:
        arguments.append(f"alias={json.dumps(field_['name'])}")
    if arguments == ["default=None"]:
        line = f"    {name}: {annotation} = None"
    elif arguments:
        line = f"    {name}: {annotation} = Field({', '.join(arguments)})"
    else:
        line = f"    {name}: {annotation}"
    return [line, *docstring([field_["description"]], 4)]


def render_object(ir_type: Json, base: str = "BaseModel") -> list[str]:
    lines = [f"class {ir_type['name']}({base}):"]
    lines += docstring([ir_type["description"]], 4)
    if base == "BaseModel":
        for field_ in ir_type["fields"]:
            lines += model_field(field_)
    if len(lines) == 1:
        lines.append("    pass")
    return lines


def render_page(ir_type: Json, item_type: Json) -> list[str]:
    shape = {(f["name"], f["required"], f["nullable"]) for f in ir_type["fields"]}
    items = next((f for f in ir_type["fields"] if f["name"] == "items"), None)
    if shape != {("items", True, False), ("nextCursor", True, True)} or (
        items is None or items["type"] != {"kind": "array", "items": item_type}
    ):
        raise GeneratorError(f"page {ir_type['name']} is not {{items, nextCursor}}")
    return render_object(ir_type, f"PageBody[{model_type(item_type)}]")


def render_enum(ir_type: Json) -> list[str]:
    values = ", ".join(json.dumps(value) for value in ir_type["values"])
    # Open (ADR-0006): the Literal lists the values known today; any other
    # string is accepted too.
    lines = [f"{ir_type['name']}: TypeAlias = Literal[{values}] | str"]
    return lines + docstring([ir_type["description"]], 0)


def render_unknown_variant(union: Json) -> list[str]:
    name = f"Unknown{union['name']}"
    wire_name = union["discriminator"]["property"]
    lines = [f"class {name}(BaseModel):"]
    lines += docstring(
        [
            f"A `{union['name']}` of a kind this version of the library "
            "doesn't know. Its other fields are kept in `model_extra`."
        ],
        4,
    )
    lines += model_field(
        {
            "name": wire_name,
            "type": {"kind": "primitive", "type": "string"},
            "required": True,
            "nullable": False,
            "description": None,
        }
    )
    return lines


def render_union(ir: Ir, union: Json) -> list[str]:
    discriminator = union["discriminator"]
    mapping: dict[str, str] = discriminator["mapping"]
    fallback = ir.fallback_of(union)
    if discriminator["kind"] == "property":
        if UNKNOWN_VARIANT in mapping:
            raise GeneratorError(f"{union['name']} has a tag {UNKNOWN_VARIANT}")
        members = [(variant, json.dumps(tag)) for tag, variant in mapping.items()]
        members.append((str(fallback), "UNKNOWN_VARIANT"))
        wire_name = discriminator["property"]
        tags = ", ".join(json.dumps(tag) for tag in mapping)
        select = (
            f"by_property({json.dumps(wire_name)}, "
            f"{json.dumps(field_name(wire_name))}, frozenset({{{tags}}}))"
        )
    else:
        markers = [(wire, variant) for wire, variant in mapping.items()]
        members = [(variant, json.dumps(variant)) for _, variant in markers]
        if fallback is not None:
            members.append((fallback, json.dumps(fallback)))
        pairs = "".join(
            f"({json.dumps(wire)}, {json.dumps(variant)}), "
            for wire, variant in markers
        )
        select = f"by_presence(({pairs}), {python_literal(fallback)})"
    variants = " | ".join(f"Annotated[{model}, Tag({tag})]" for model, tag in members)
    lines = [
        f"{union['name']}: TypeAlias = Annotated[",
        f"    {variants},",
        f"    Discriminator({select}),",
        "]",
    ]
    return lines + docstring([union["description"]], 0)


def render_models(ir: Ir) -> tuple[str, list[str]]:
    pages = ir.page_types()
    blocks: dict[str, list[str]] = {}
    deps: dict[str, set[str]] = {}
    for name, ir_type in ir.types.items():
        deps[name] = dependencies(ir, ir_type)
        if ir_type["kind"] == "enum":
            blocks[name] = render_enum(ir_type)
        elif ir_type["kind"] == "union":
            blocks[name] = render_union(ir, ir_type)
            fallback = ir.fallback_of(ir_type)
            if ir_type["discriminator"]["kind"] == "property" and (
                fallback != ir.unknown_event
            ):
                if fallback in ir.types:
                    raise GeneratorError(f"{fallback} collides with an IR type")
                blocks[str(fallback)] = render_unknown_variant(ir_type)
                deps[str(fallback)] = set()
        elif name in pages:
            blocks[name] = render_page(ir_type, pages[name])
            deps[name] = set(refs(pages[name]))
        else:
            blocks[name] = render_object(ir_type)
    order = topological(blocks, deps)
    header = [
        "from datetime import datetime",
        "from typing import Annotated, Any, Literal, TypeAlias",
        "",
        "from pydantic import Discriminator, Field, Tag",
        "",
        "from .._core._models import BaseModel",
        "from .._core._pagination import PageBody",
        "from .._core._unions import UNKNOWN_VARIANT, by_presence, by_property",
    ]
    body = [line for name in order for line in ["", "", *blocks[name]]]
    return module(header, body), order


# --- request params ----------------------------------------------------------


@dataclass
class BodyPlan:
    """How one method's body maps onto keyword arguments."""

    fields: list[Json]
    # Top-level field -> the type its argument takes instead of the IR's.
    narrowed: dict[str, Json]
    # Top-level field -> {nested wire name: pinned value}.
    pinned: dict[str, dict[str, Json]]


def body_plan(ir: Ir, method: Json) -> BodyPlan | None:
    request_body = method["requestBody"]
    if request_body is None:
        return None
    body_type = ir.types[request_body["type"]["name"]]
    if body_type["kind"] != "object":
        raise GeneratorError(f"{method['operationId']}: body is not an object")
    plan = BodyPlan(list(body_type["fields"]), {}, {})
    by_name = {f["name"]: f for f in body_type["fields"]}
    for constraint in request_body["constraints"]:
        path = constraint["path"]
        top = by_name.get(path[0])
        if top is None:
            raise GeneratorError(f"{method['operationId']}: no field {path[0]}")
        if constraint["kind"] == "variant" and len(path) == 1:
            union = ir.types[top["type"]["name"]]
            variant = union["discriminator"]["mapping"][constraint["requiredProperty"]]
            plan.narrowed[path[0]] = {"kind": "ref", "name": variant}
        elif constraint["kind"] == "const" and len(path) == 2:
            plan.pinned.setdefault(path[0], {})[path[1]] = constraint["value"]
        else:
            raise GeneratorError(f"{method['operationId']}: constraint {constraint}")
    return plan


def param_type(ir: Ir, type_ref: Json) -> str:
    kind = type_ref["kind"]
    if kind == "primitive":
        if type_ref["type"] == "binary":
            return "FileInput"
        if type_ref["type"] in ("json",):
            raise GeneratorError("json values in request bodies have no rule")
        return PRIMITIVES[type_ref["type"]]
    if kind == "ref":
        if ir.kind(type_ref["name"]) == "enum":
            return str(type_ref["name"])
        return f"{type_ref['name']}Param"
    if kind == "array":
        return f"Sequence[{param_type(ir, type_ref['items'])}]"
    raise GeneratorError("maps in request bodies have no rule")


def param_types(ir: Ir) -> tuple[list[str], dict[str, set[str]]]:
    """Every object or union a caller passes as a nested body value, and the
    fields each one leaves out because a method pins them."""
    omitted: dict[str, set[str]] = {}
    roots: list[str] = []
    for _, method in ir.methods:
        plan = body_plan(ir, method)
        if plan is None:
            continue
        for field_ in plan.fields:
            type_ref = plan.narrowed.get(field_["name"], field_["type"])
            roots += refs(type_ref)
            for name in refs(type_ref):
                pins = set(plan.pinned.get(field_["name"], {}))
                if omitted.setdefault(name, pins) != pins:
                    raise GeneratorError(f"{name} is pinned differently by methods")
    reached: list[str] = []
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name in reached or ir.kind(name) == "enum":
            continue
        reached.append(name)
        pending += dependencies(ir, ir.types[name], unknown=False)
    return sorted(reached), omitted


def render_params(ir: Ir) -> tuple[str, list[str]]:
    names, omitted = param_types(ir)
    blocks: dict[str, list[str]] = {}
    deps: dict[str, set[str]] = {}
    enums: set[str] = set()
    for name in names:
        ir_type = ir.types[name]
        param = f"{name}Param"
        if param in ir.types:
            raise GeneratorError(f"{param} collides with an IR type")
        deps[param] = {
            f"{dep}Param"
            for dep in dependencies(ir, ir_type, unknown=False)
            if ir.kind(dep) != "enum"
        }
        if ir_type["kind"] == "union":
            members = variants(ir, ir_type, unknown=False)
            alias = " | ".join(f"{variant}Param" for variant in members)
            blocks[param] = [f"{param}: TypeAlias = {alias}"]
            blocks[param] += docstring([ir_type["description"]], 0)
            continue
        lines = [f"class {param}(TypedDict, total=False):"]
        lines += docstring([ir_type["description"]], 4)
        for field_ in ir_type["fields"]:
            if field_["name"] in omitted.get(name, set()):
                continue
            key = snake(field_["name"])
            if keyword.iskeyword(key) or camel(key) != field_["name"]:
                raise GeneratorError(f"{name}.{field_['name']} has no snake_case key")
            annotation = param_type(ir, field_["type"])
            enums.update(n for n in refs(field_["type"]) if ir.kind(n) == "enum")
            if field_["nullable"]:
                annotation += " | None"
            if field_["required"]:
                annotation = f"Required[{annotation}]"
            lines.append(f"    {key}: {annotation}")
            lines += docstring([field_["description"]], 4)
        if len(lines) == 1:
            lines.append("    pass")
        blocks[param] = lines
    header = [
        "from collections.abc import Sequence",
        "from datetime import datetime",
        "from typing import TypeAlias",
        "",
        "from typing_extensions import Required, TypedDict",
        "",
        "from .._core._files import FileInput",
    ]
    if enums:
        header.append(f"from ._models import {', '.join(sorted(enums))}")
    order = topological(blocks, deps)
    body = [line for name in order for line in ["", "", *blocks[name]]]
    return module(header, body), order


# --- resources ---------------------------------------------------------------


@dataclass
class Argument:
    name: str
    annotation: str
    required: bool
    description: str | None = None
    nullable: bool = False

    def signature(self) -> str:
        null = " | None" if self.nullable else ""
        if self.required:
            return f"{self.name}: {self.annotation}{null}"
        return f"{self.name}: {self.annotation} | NotGiven{null} = NOT_GIVEN"


@dataclass
class MethodPlan:
    name: str
    positional: list[Argument]
    keywords: list[Argument]
    returns: str
    call: str
    request: list[str]
    response_type: str | None
    pagination: Json | None
    docs: list[str | None]


def response_plan(ir: Ir, method: Json) -> tuple[str, str, str | None]:
    """(return annotation, pipeline method, response type argument)."""
    response = method["response"]
    kind = response["kind"]
    if kind == "model":
        name = response["type"]["name"]
        if ir.kind(name) == "union":
            return name, "request_union", f"_{constant(name)}"
        return name, "request", name
    if kind == "operation":
        return response["type"]["name"], "request", response["type"]["name"]
    if kind == "writeResult":
        name = response["type"]["name"]
        if "created" not in {f["name"] for f in ir.types[name]["fields"]}:
            raise GeneratorError(f"write result {name} has no `created` field")
        return name, "request_write_result", name
    if kind == "page":
        item = model_type(method["pagination"]["itemType"])
        return f"{{page}}[{item}]", "request_page", response["type"]["name"]
    if kind == "empty":
        return "None", "request_empty", None
    if kind == "binary":
        return "BinaryResponse", "request_binary", None
    raise GeneratorError(f"no rule for {kind} responses")


def plan_method(ir: Ir, method: Json) -> MethodPlan:
    operation = method["operationId"]
    template = method["path"]["template"]
    if method["orgScoped"] != ("{orgId}" in template):
        raise GeneratorError(f"{operation}: orgScoped disagrees with the path")
    if method["headerParams"]:
        raise GeneratorError(f"{operation}: header parameters have no rule")
    if any(p["name"] == "orgId" for p in method["pathParams"]):
        raise GeneratorError(f"{operation}: orgId must come from the binding")
    path = template
    if method["path"]["customVerb"] is not None:
        path += ":" + method["path"]["customVerb"]

    positional = [
        Argument(identifier(p["name"]), "str", True, p["description"])
        for p in method["pathParams"]
    ]
    for p in method["pathParams"]:
        if p["type"] != {"kind": "primitive", "type": "string"} or not p["required"]:
            raise GeneratorError(f"{operation}: path parameter {p['name']}")
    keywords: list[Argument] = []
    request = [json.dumps(method["httpMethod"]), json.dumps(path)]
    if positional:
        params = ", ".join(
            f"{json.dumps(p['name'])}: {identifier(p['name'])}"
            for p in method["pathParams"]
        )
        request.append(f"path_params={{{params}}}")

    if method["ifMatch"] == "required":
        keywords.append(Argument("if_match", "str", True, IF_MATCH_DOC))

    plan = body_plan(ir, method)
    if plan is not None:
        entries = []
        for field_ in plan.fields:
            name = identifier(field_["name"])
            pins = plan.pinned.get(field_["name"])
            type_ref = plan.narrowed.get(field_["name"], field_["type"])
            keywords.append(
                Argument(
                    name,
                    param_type(ir, type_ref),
                    field_["required"],
                    field_["description"],
                    nullable=field_["nullable"],
                )
            )
            if pins is None:
                value = name
            else:
                fixed = ", ".join(
                    f"{json.dumps(snake(k))}: {python_literal(v)}"
                    for k, v in pins.items()
                )
                value = f"with_fixed({name}, {{{fixed}}})"
            entries.append(f"{json.dumps(field_['name'])}: {value}")
        request.append(f"body={{{', '.join(entries)}}}")
        content_type = method["requestBody"]["contentType"]
        if content_type != "application/json":
            request.append(f"content_type={json.dumps(content_type)}")
        binary_parts = method["requestBody"]["binaryParts"]
        if binary_parts:
            parts = ", ".join(
                f"{json.dumps(p['name'])}: {json.dumps(p['contentType'])}"
                for p in binary_parts
            )
            request.append(f"binary_parts={{{parts}}}")

    if method["queryParams"]:
        entries = []
        for p in method["queryParams"]:
            name = identifier(p["name"])
            annotation = param_type(ir, p["type"])
            keywords.append(Argument(name, annotation, p["required"], p["description"]))
            entries.append(f"{json.dumps(p['name'])}: {name}")
        request.append(f"query={{{', '.join(entries)}}}")

    headers = []
    if method["ifMatch"] == "required":
        headers.append('"if-match": if_match')
    elif method["ifMatch"] == "optional":
        keywords.append(Argument("if_match", "str", False, IF_MATCH_DOC))
        headers.append('"if-match": if_match')
    if method["ifNoneMatch"] != "none":
        required = method["ifNoneMatch"] == "required"
        keywords.append(Argument("if_none_match", "str", required, IF_NONE_MATCH_DOC))
        headers.append('"if-none-match": if_none_match')
    if method["response"]["kind"] == "binary":
        headers.append(f'"accept": {json.dumps(method["response"]["contentType"])}')
    if headers:
        request.append(f"headers={{{', '.join(headers)}}}")

    if method["orgScoped"]:
        request.append("org_scoped=True")
    if method["security"]["kind"] == "none":
        request.append("authenticated=False")
    if method["retrySafe"]:
        request.append("retry_safe=True")
    options = ["max_retries=max_retries", "timeout=timeout"]
    if method["idempotencyKey"] != "none":
        if method["idempotencyKey"] == "required":
            request.append("idempotency_key_required=True")
        keywords.append(Argument("idempotency_key", "str", False, IDEMPOTENCY_DOC))
        options.append("idempotency_key=idempotency_key")
    keywords.append(Argument("max_retries", "int", False, MAX_RETRIES_DOC))
    keywords.append(Argument("timeout", "float | httpx.Timeout", False, TIMEOUT_DOC))
    request.append(f"options=RequestOptions({', '.join(options)})")

    names = [a.name for a in positional + keywords]
    if len(set(names)) != len(names):
        raise GeneratorError(f"{operation}: argument names collide")

    returns, call, response_type = response_plan(ir, method)
    pagination = None
    if call == "request_page":
        pagination = method["pagination"]
        if pagination["style"] not in ("cursor", "after"):
            raise GeneratorError(f"{operation}: no rule for {pagination['style']}")
    return MethodPlan(
        name=identifier(method["name"]),
        positional=positional,
        keywords=keywords,
        returns=returns,
        call=call,
        request=request,
        response_type=response_type,
        pagination=pagination,
        docs=[method["summary"], method["description"], RETURN_DOCS.get(call)],
    )


IF_MATCH_DOC = "The ETag the object was read with (`last_response.etag`)."
IF_NONE_MATCH_DOC = "An ETag the caller already holds."
IDEMPOTENCY_DOC = (
    "Overrides the key generated for this call. Retries reuse the same key."
)
MAX_RETRIES_DOC = "Overrides the client's `max_retries` for this call."
TIMEOUT_DOC = "Overrides the client's `timeout` for this call, in seconds."
RETURN_DOCS = {
    "request_empty": "Returns `None`: the API answers 204 No Content.",
    "request_write_result": (
        "`created` is true when this call created the Learner (201) and false "
        "when it already existed (200)."
    ),
    "request_binary": "Returns the file's bytes with its content type and filename.",
}


def python_literal(value: Json) -> str:
    return repr(value)


def render_method(plan: MethodPlan, asynchronous: bool) -> list[str]:
    page = "AsyncPage" if asynchronous else "SyncPage"
    returns = plan.returns.replace("{page}", page)
    parameters = ["self"]
    parameters += [a.signature() for a in plan.positional]
    if plan.positional:
        parameters.append("/")
    parameters.append("*")
    parameters += [a.signature() for a in plan.keywords]
    prefix = "async def" if asynchronous else "def"
    lines = [f"    {prefix} {plan.name}("]
    lines += [f"        {parameter}," for parameter in parameters]
    lines.append(f"    ) -> {returns}:")
    described = [a for a in plan.positional + plan.keywords if a.description]
    args = "Args:\n" + "\n".join(f"    {a.name}: {a.description}" for a in described)
    lines += docstring([*plan.docs, args if described else None], 8)
    arguments = [f"ApiRequest({', '.join(plan.request)})"]
    if plan.response_type is not None:
        arguments.append(plan.response_type)
    if plan.pagination is not None:
        arguments.append(f"cursor_param={json.dumps(plan.pagination['cursorParam'])}")
        arguments.append(f"style={json.dumps(plan.pagination['style'])}")
    awaiting = "await " if asynchronous else ""
    call = f"{awaiting}self._pipeline.{plan.call}({', '.join(arguments)})"
    lines.append(f"        {'' if plan.returns == 'None' else 'return '}{call}")
    return lines


@dataclass
class ResourceNode:
    path: tuple[str, ...]
    methods: list[Json] = field(default_factory=list)
    children: dict[str, ResourceNode] = field(default_factory=dict)

    @property
    def class_name(self) -> str:
        return "".join(pascal(part) for part in self.path)

    def walk(self) -> Iterator[ResourceNode]:
        """Children before parents, so a class is defined before its use."""
        for name in sorted(self.children):
            yield from self.children[name].walk()
        yield self


def is_extended(node: ResourceNode) -> bool:
    return ".".join(node.path) in EXTENDED_RESOURCES


def exposing_module(node: ResourceNode) -> str:
    """The module, relative to `resources/`, of the classes the client
    exposes for a top-level resource."""
    module_name = identifier(node.path[0])
    return f".._extensions.{module_name}" if is_extended(node) else f".{module_name}"


def check_extensions(roots: Mapping[str, ResourceNode]) -> None:
    nodes = {
        ".".join(node.path): node for root in roots.values() for node in root.walk()
    }
    for path in sorted(EXTENDED_RESOURCES):
        node = nodes.get(path)
        if node is None:
            raise GeneratorError(f"extended resource {path} is not in the IR")
        # A nested extension would import its parent's module, which would
        # import it back.
        if len(node.path) != 1:
            raise GeneratorError(f"extended resource {path} is not top-level")
        extension = EXTENSIONS / f"{identifier(node.path[0])}.py"
        if not extension.is_file():
            raise GeneratorError(f"extended resource {path} needs {extension}")


def resource_tree(ir: Ir) -> dict[str, ResourceNode]:
    roots: dict[str, ResourceNode] = {}
    for path, method in ir.methods:
        node = roots.setdefault(path[0], ResourceNode(path[:1]))
        for depth in range(1, len(path)):
            node = node.children.setdefault(
                path[depth], ResourceNode(path[: depth + 1])
            )
        node.methods.append(method)
    return roots


def render_resource_class(
    ir: Ir, node: ResourceNode, asynchronous: bool
) -> tuple[list[str], set[str]]:
    variant = "Async" if asynchronous else ""
    base = "AsyncAPIResource" if asynchronous else "SyncAPIResource"
    pipeline = "AsyncPipeline" if asynchronous else "SyncPipeline"
    suffix = "Base" if is_extended(node) else ""
    lines = [f"class {variant}{node.class_name}{suffix}({base}):"]
    if suffix:
        subclass = f"{variant}{node.class_name}"
        module_name = identifier(node.path[0])
        lines += docstring(
            [
                f"The generated methods of `{'.'.join(node.path)}`. The client "
                f"exposes the hand-written subclass `{subclass}` in "
                f"`_extensions/{module_name}.py`."
            ],
            4,
        )
    used: set[str] = set()
    if node.children:
        for name, child in sorted(node.children.items()):
            lines.append(f"    {identifier(name)}: {variant}{child.class_name}")
        lines += ["", f"    def __init__(self, pipeline: {pipeline}) -> None:"]
        lines.append("        super().__init__(pipeline)")
        for name, child in sorted(node.children.items()):
            child_class = f"{variant}{child.class_name}"
            lines.append(f"        self.{identifier(name)} = {child_class}(pipeline)")
    for method in sorted(node.methods, key=lambda m: identifier(m["name"])):
        plan = plan_method(ir, method)
        if len(lines) > 1:
            lines.append("")
        lines += render_method(plan, asynchronous)
        signature_text = "\n".join(
            [a.annotation for a in plan.positional + plan.keywords]
            + [plan.returns, plan.response_type or ""]
        )
        used.update(re.findall(r"\b[A-Z]\w*", signature_text))
    return lines, used


def render_resource(ir: Ir, root: ResourceNode) -> str:
    body: list[str] = []
    used: set[str] = set()
    adapters: dict[str, str] = {}
    for node in root.walk():
        for method in node.methods:
            returns, call, response_type = response_plan(ir, method)
            if call == "request_union" and response_type is not None:
                adapters[response_type] = returns
        for asynchronous in (False, True):
            lines, names = render_resource_class(ir, node, asynchronous)
            body += ["", "", *lines]
            used |= names
    type_names = sorted(
        name
        for name in used
        if name in ir.types or (name.endswith("Param") and name[:-5] in ir.types)
    )
    class_names = {
        f"{variant}{node.class_name}{suffix}"
        for node in root.walk()
        for variant in ("", "Async")
        for suffix in ("", "Base")
    }
    if class_names & set(type_names):
        raise GeneratorError(f"resource classes collide with types in {root.path}")
    header = [
        "from collections.abc import Sequence",
        "from datetime import datetime",
        "",
        "import httpx",
        "from pydantic import TypeAdapter",
        "",
        "from .._core._files import FileInput",
        "from .._core._models import BinaryResponse",
        "from .._core._pagination import AsyncPage, SyncPage",
        "from .._core._pipeline import AsyncPipeline, SyncPipeline",
        "from .._core._request import ApiRequest, RequestOptions, with_fixed",
        "from .._core._resource import AsyncAPIResource, SyncAPIResource",
        "from .._core._sentinel import NOT_GIVEN, NotGiven",
    ]
    if type_names:
        header.append(f"from ..types import {', '.join(type_names)}")
    adapter_lines = [
        f"{constant_name}: TypeAdapter[{type_name}] = TypeAdapter({type_name})"
        for constant_name, type_name in sorted(adapters.items())
    ]
    if adapter_lines:
        body = ["", "", *adapter_lines, *body]
    return module(header, body)


def render_root(roots: Mapping[str, ResourceNode]) -> str:
    header = ["from .._core._pipeline import AsyncPipeline, SyncPipeline"]
    for node in roots.values():
        header.append(
            f"from {exposing_module(node)} import "
            f"Async{node.class_name}, {node.class_name}"
        )
    body: list[str] = []
    for variant, pipeline in (("Sync", "SyncPipeline"), ("Async", "AsyncPipeline")):
        prefix = "" if variant == "Sync" else "Async"
        lines = [f"class {variant}Resources:"]
        lines += docstring(["Every top-level resource, attached to a client."], 4)
        for name, node in sorted(roots.items()):
            lines.append(f"    {identifier(name)}: {prefix}{node.class_name}")
        lines += ["", f"    def __init__(self, pipeline: {pipeline}) -> None:"]
        for name, node in sorted(roots.items()):
            lines.append(
                f"        self.{identifier(name)} = {prefix}{node.class_name}(pipeline)"
            )
        body += ["", "", *lines]
    return module(header, body)


def render_reexports(modules: Mapping[str, list[str]]) -> str:
    """Re-exports names from modules given relative to the package, such as
    `._models`."""
    header = []
    names: list[str] = []
    for module_name, exported in sorted(modules.items()):
        header.append(f"from {module_name} import {', '.join(sorted(exported))}")
        names += exported
    body = ["", "__all__ = [", *[f"    {json.dumps(n)}," for n in sorted(names)], "]"]
    return module(header, body)


def module(header: list[str], body: list[str]) -> str:
    return "\n".join([BANNER, *header, *body]) + "\n"


# --- driver -------------------------------------------------------------------


def generate(ir: Ir) -> dict[str, str]:
    """Relative path under the package -> file contents (before formatting)."""
    models, model_names = render_models(ir)
    params, param_names = render_params(ir)
    files = {
        "types/_models.py": models,
        "types/_params.py": params,
        "types/__init__.py": render_reexports(
            {"._models": model_names, "._params": param_names}
        ),
    }
    roots = resource_tree(ir)
    check_extensions(roots)
    for name, root in roots.items():
        files[f"resources/{identifier(name)}.py"] = render_resource(ir, root)
    files["resources/_root.py"] = render_root(roots)
    files["resources/__init__.py"] = render_reexports(
        {
            exposing_module(node): [node.class_name, f"Async{node.class_name}"]
            for node in roots.values()
        }
    )
    return files


def write_formatted(files: Mapping[str, str], out: Path) -> None:
    for relative, contents in files.items():
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
    paths = [str(out / relative) for relative in sorted(files)]
    ruff = [sys.executable, "-m", "ruff"]
    config = ["--config", str(ROOT / "pyproject.toml")]
    subprocess.run(  # noqa: S603
        [*ruff, "check", *config, "--quiet", "--fix", "--select", "F401,I", *paths],
        check=True,
    )
    subprocess.run([*ruff, "format", *config, "--quiet", *paths], check=True)  # noqa: S603


def load_ir() -> Ir:
    raw = json.loads(IR_PATH.read_text())
    jsonschema.validate(raw, json.loads(SCHEMA_PATH.read_text()))
    return Ir(raw)


def generated_files(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)): path.read_text()
        for name in GENERATED_DIRS
        for path in sorted((directory / name).glob("*.py"))
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="fail if the files are stale"
    )
    arguments = parser.parse_args()
    try:
        files = generate(load_ir())
    except GeneratorError as error:
        print(f"generate.py: {error}", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as scratch:
        out = Path(scratch)
        write_formatted(files, out)
        fresh = generated_files(out)
    current = generated_files(PACKAGE)
    if arguments.check:
        stale = sorted(set(fresh) ^ set(current)) + sorted(
            name for name in fresh if current.get(name) != fresh[name]
        )
        for name in stale:
            sys.stdout.writelines(
                difflib.unified_diff(
                    current.get(name, "").splitlines(keepends=True),
                    fresh.get(name, "").splitlines(keepends=True),
                    f"a/{name}",
                    f"b/{name}",
                )
            )
        return 1 if stale else 0
    for name in GENERATED_DIRS:
        shutil.rmtree(PACKAGE / name)
    for name, contents in fresh.items():
        target = PACKAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
    return 0


if __name__ == "__main__":
    sys.exit(main())
