"""Generate the resource and model layer from the vendored SDK IR.

    uv run python scripts/generate.py          # rewrite the generated files
    uv run python scripts/generate.py --check  # fail if they are stale

Reads only `openapi/sdk-ir.json` (validated against `sdk-ir.schema.json`) and
writes `src/teachmehipaa/types/`, `src/teachmehipaa/resources/`, the
Markdown reference `docs/reference/resources.md` and the API reference's
Python samples, `docs/reference/code-samples.json`. The output is
byte-for-byte deterministic, and the Python is ruff-formatted. Any IR shape
this generator has no rule for stops it with an error rather than guessing.
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
REFERENCE = ROOT / "docs" / "reference" / "resources.md"
CODE_SAMPLES = ROOT / "docs" / "reference" / "code-samples.json"
OPENAPI_VERSION = ROOT / "OPENAPI_VERSION"
# Samples are formatted in the scratch directory under this name.
SAMPLES_DIR = "_samples"

# Top-level resources with hand-written methods, by IR path. The generator
# names their classes `<Name>Base` and `Async<Name>Base`;
# `_extensions/<module>.py` subclasses them under the plain names, and the
# client exposes those subclasses.
EXTENDED_RESOURCES = frozenset({"events"})
# What each extended resource's hand-written methods add, for the Markdown
# reference; the IR doesn't know them.
EXTENSION_DOCS = {
    "events": (
        "`client.events.tail(...)` is written by hand rather than generated. "
        "It walks the Event log from a saved position, stopping once caught "
        "up or following new Events. See [The Event log](../guides/events.md"
        "#follow-the-log-from-where-you-left-off)."
    ),
}

# The type of an Operation's `response`, by operationId, where the spec leaves
# it untyped but the API documents it. Types come from `_operations.py`.
OPERATION_RESPONSES = {
    "redriveWebhookSubscription": "WebhookDeliveryResult",
    "testWebhookSubscription": "WebhookDeliveryResult",
}

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

    The first paragraph is the summary and always ends a sentence. Each
    line of a paragraph wraps on its own, so lists stay lists; a list item
    or an `Args:` entry continues one level deeper than it starts.
    """
    width = LINE_LENGTH - indent
    texts = [
        p.replace("\\", "\\\\").replace('"""', '\\"\\"\\"') for p in paragraphs if p
    ]
    if not texts:
        return []
    # PEP 257: the summary is a sentence. The IR's method summaries are
    # titles, such as "List all learners".
    if not texts[0].rstrip().endswith((".", "?", "!")):
        texts[0] = texts[0].rstrip() + "."
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

    def tagged_fields(self) -> dict[str, tuple[str, list[str]]]:
        """Variant model -> (its discriminator's wire name, the tags that
        select it), for every property union. The fallback isn't a key: its
        discriminator stays an open string."""
        tagged: dict[str, tuple[str, list[str]]] = {}
        for union in self.types.values():
            discriminator = union.get("discriminator")
            if union["kind"] != "union" or discriminator["kind"] != "property":
                continue
            wire_name = discriminator["property"]
            for tag, variant in discriminator["mapping"].items():
                field_ = next(
                    (
                        f
                        for f in self.types[variant]["fields"]
                        if f["name"] == wire_name
                    ),
                    None,
                )
                if field_ is None or (
                    field_["type"] != {"kind": "primitive", "type": "string"}
                    or not field_["required"]
                    or field_["nullable"]
                ):
                    raise GeneratorError(f"{variant}.{wire_name} is not a required tag")
                name, tags = tagged.setdefault(variant, (wire_name, []))
                if name != wire_name:
                    raise GeneratorError(f"{variant} is tagged by two properties")
                tags.append(tag)
        return tagged

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


def tag_literal(tags: Iterable[str]) -> str:
    return f"Literal[{', '.join(json.dumps(tag) for tag in tags)}]"


def model_field(field_: Json, tags: list[str] | None = None) -> list[str]:
    """`tags`, when given, are the only values a variant's discriminator
    takes, so it is typed as their Literal for type checkers to narrow on."""
    name = field_name(field_["name"])
    annotation = model_type(field_["type"]) if tags is None else tag_literal(tags)
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


def render_object(
    ir_type: Json,
    base: str = "BaseModel",
    tagged: tuple[str, list[str]] | None = None,
) -> list[str]:
    lines = [f"class {ir_type['name']}({base}):"]
    lines += docstring([ir_type["description"]], 4)
    if base == "BaseModel":
        for field_ in ir_type["fields"]:
            tags = None
            if tagged is not None and field_["name"] == tagged[0]:
                tags = tagged[1]
            lines += model_field(field_, tags)
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
        select = f"by_presence(({pairs}), {fallback!r})"
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
    tagged = ir.tagged_fields()
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
            blocks[name] = render_object(ir_type, tagged=tagged.get(name))
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
    tagged = ir.tagged_fields()
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
            wire_name, tags = tagged.get(name, (None, []))
            if field_["name"] == wire_name:
                annotation = tag_literal(tags)
            else:
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
        "from typing import Literal, TypeAlias",
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
    # A literal default in place of `NOT_GIVEN`.
    default: str | None = None

    def signature(self) -> str:
        null = " | None" if self.nullable else ""
        if self.default is not None:
            return f"{self.name}: {self.annotation}{null} = {self.default}"
        if self.required:
            return f"{self.name}: {self.annotation}{null}"
        return f"{self.name}: {self.annotation} | NotGiven{null} = NOT_GIVEN"


@dataclass
class Overload:
    """One `@overload` of a method: the keyword arguments it types narrower
    than the implementation, by name, and what it returns."""

    arguments: dict[str, str]
    returns: str


@dataclass
class MethodPlan:
    name: str
    positional: list[Argument]
    keywords: list[Argument]
    returns: str
    call: str
    request: list[str]
    response_type: str | None
    cursor_param: str | None
    position_field: str | None
    docs: list[str | None]
    overloads: list[Overload] = field(default_factory=list)


@dataclass
class Arguments:
    """A method's parameters and the `ApiRequest` arguments that send them,
    collected by the planning steps in signature order."""

    positional: list[Argument] = field(default_factory=list)
    keywords: list[Argument] = field(default_factory=list)
    request: list[str] = field(default_factory=list)


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
        if response["type"]["name"] != "Operation":
            raise GeneratorError(f"no rule for {response['type']['name']} operations")
        # `{operation}` becomes `Operation` or `AsyncOperation`, the
        # hand-written subclasses with `wait()`.
        result = OPERATION_RESPONSES.get(method["operationId"])
        returns = "{operation}" if result is None else f"{{operation}}[{result}]"
        return returns, "request_operation", returns
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


def request_path(method: Json) -> str:
    """The path template the method sends, with a custom method's verb."""
    operation = method["operationId"]
    template = method["path"]["template"]
    if method["orgScoped"] != ("{orgId}" in template):
        raise GeneratorError(f"{operation}: orgScoped disagrees with the path")
    if method["headerParams"]:
        raise GeneratorError(f"{operation}: header parameters have no rule")
    if any(p["name"] == "orgId" for p in method["pathParams"]):
        raise GeneratorError(f"{operation}: orgId must come from the binding")
    if method["path"]["customVerb"] is None:
        return str(template)
    return f"{template}:{method['path']['customVerb']}"


def plan_path_params(method: Json, arguments: Arguments) -> None:
    for p in method["pathParams"]:
        if p["type"] != {"kind": "primitive", "type": "string"} or not p["required"]:
            raise GeneratorError(f"{method['operationId']}: path parameter {p['name']}")
        arguments.positional.append(
            Argument(identifier(p["name"]), "str", True, p["description"])
        )
    if method["pathParams"]:
        params = ", ".join(
            f"{json.dumps(p['name'])}: {identifier(p['name'])}"
            for p in method["pathParams"]
        )
        arguments.request.append(f"path_params={{{params}}}")


def plan_body(ir: Ir, method: Json, arguments: Arguments) -> None:
    plan = body_plan(ir, method)
    if plan is None:
        return
    entries = []
    for field_ in plan.fields:
        name = identifier(field_["name"])
        pins = plan.pinned.get(field_["name"])
        type_ref = plan.narrowed.get(field_["name"], field_["type"])
        arguments.keywords.append(
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
            fixed = ", ".join(f"{json.dumps(snake(k))}: {v!r}" for k, v in pins.items())
            value = f"with_fixed({name}, {{{fixed}}})"
        entries.append(f"{json.dumps(field_['name'])}: {value}")
    arguments.request.append(f"body={{{', '.join(entries)}}}")
    content_type = method["requestBody"]["contentType"]
    if content_type != "application/json":
        arguments.request.append(f"content_type={json.dumps(content_type)}")
    binary_parts = method["requestBody"]["binaryParts"]
    if binary_parts:
        parts = ", ".join(
            f"{json.dumps(p['name'])}: {json.dumps(p['contentType'])}"
            for p in binary_parts
        )
        arguments.request.append(f"binary_parts={{{parts}}}")


def plan_query(ir: Ir, method: Json, arguments: Arguments) -> None:
    if not method["queryParams"]:
        return
    entries = []
    for p in method["queryParams"]:
        name = identifier(p["name"])
        annotation = param_type(ir, p["type"])
        arguments.keywords.append(
            Argument(name, annotation, p["required"], p["description"])
        )
        entries.append(f"{json.dumps(p['name'])}: {name}")
    arguments.request.append(f"query={{{', '.join(entries)}}}")


def plan_conditionals(method: Json, arguments: Arguments) -> None:
    """If-Match, If-None-Match and a binary download's `stream`. A required
    `if_match` is planned earlier: it leads the keywords."""
    if method["ifMatch"] != "none":
        if method["ifMatch"] == "optional":
            arguments.keywords.append(
                Argument("if_match", "ETagSource", False, IF_MATCH_DOC)
            )
        arguments.request.append("if_match=if_match")
    if method["ifNoneMatch"] != "none":
        required = method["ifNoneMatch"] == "required"
        arguments.keywords.append(
            Argument("if_none_match", "ETagSource", required, IF_NONE_MATCH_DOC)
        )
        arguments.request.append("if_none_match=if_none_match")
    if method["response"]["kind"] == "binary":
        content_type = method["response"]["contentType"]
        arguments.request.append(f"binary_content_type={json.dumps(content_type)}")
        arguments.keywords.append(
            Argument("stream", "bool", False, STREAM_DOC, default="False")
        )


def plan_request_flags(method: Json, arguments: Arguments) -> None:
    if method["orgScoped"]:
        arguments.request.append("org_scoped=True")
    if method["security"]["kind"] == "none":
        arguments.request.append("authenticated=False")
    if method["retrySafe"]:
        arguments.request.append("retry_safe=True")


def plan_options(method: Json, arguments: Arguments) -> None:
    """The per-call overrides every method takes, plus an idempotency key
    where the IR marks one."""
    options = ["max_retries=max_retries", "timeout=timeout"]
    if method["idempotencyKey"] != "none":
        if method["idempotencyKey"] == "required":
            arguments.request.append("idempotency_key_required=True")
        arguments.keywords.append(
            Argument("idempotency_key", "str", False, IDEMPOTENCY_DOC)
        )
        options.append("idempotency_key=idempotency_key")
    arguments.keywords.append(Argument("max_retries", "int", False, MAX_RETRIES_DOC))
    arguments.keywords.append(
        Argument("timeout", "float | httpx.Timeout", False, TIMEOUT_DOC)
    )
    arguments.keywords.append(Argument("request_id", "str", False, REQUEST_ID_DOC))
    options.append("request_id=request_id")
    arguments.request.append(f"options=RequestOptions({', '.join(options)})")


def plan_return(ir: Ir, method: Json) -> tuple[str, str, str | None, list[Overload]]:
    """(return annotation, pipeline method, response type argument,
    overloads), with conditional reads and downloads typed by their
    arguments."""
    operation = method["operationId"]
    returns, call, response_type = response_plan(ir, method)
    overloads: list[Overload] = []
    if method["ifNoneMatch"] != "none":
        if call != "request":
            raise GeneratorError(f"{operation}: If-None-Match on a non-model read")
        call = "request_conditional"
        conditional = f"{returns} | NotModified"
        if method["ifNoneMatch"] == "optional":
            # Without If-None-Match a 304 can't happen, so a plain call is
            # typed as the model alone.
            overloads = [
                Overload(
                    {"if_none_match": "if_none_match: NotGiven = NOT_GIVEN"}, returns
                ),
                Overload({"if_none_match": "if_none_match: ETagSource"}, conditional),
            ]
        returns = conditional
    if call == "request_binary":
        stream = "{stream}"
        overloads = [
            Overload({"stream": "stream: Literal[False] = False"}, returns),
            Overload({"stream": "stream: Literal[True]"}, stream),
            Overload({"stream": "stream: bool"}, f"{returns} | {stream}"),
        ]
        returns = f"{returns} | {stream}"
    return returns, call, response_type, overloads


def position_field(ir: Ir, method: Json) -> str | None:
    """The item attribute an `after` list's next page starts after: the
    item's own id, `<itemType>Id`, which every variant must carry."""
    pagination = method["pagination"]
    operation = method["operationId"]
    if pagination["style"] == "cursor":
        return None
    if pagination["style"] != "after":
        raise GeneratorError(f"{operation}: no rule for {pagination['style']}")
    item = pagination["itemType"]
    if item["kind"] != "ref":
        raise GeneratorError(f"{operation}: an `after` list of non-models")
    name = item["name"]
    wire_name = f"{name[:1].lower()}{name[1:]}Id"
    item_type = ir.types[name]
    models = (
        variants(ir, item_type, unknown=True)
        if item_type["kind"] == "union"
        else [name]
    )
    for model in models:
        id_field = next(
            (f for f in ir.types[model]["fields"] if f["name"] == wire_name), None
        )
        if id_field is None or (
            id_field["type"] != {"kind": "primitive", "type": "string"}
            or not id_field["required"]
        ):
            raise GeneratorError(f"{operation}: {model} has no {wire_name} to page by")
    return field_name(wire_name)


def plan_method(ir: Ir, method: Json) -> MethodPlan:
    arguments = Arguments(
        request=[json.dumps(method["httpMethod"]), json.dumps(request_path(method))]
    )
    plan_path_params(method, arguments)
    if method["ifMatch"] == "required":
        arguments.keywords.append(
            Argument("if_match", "ETagSource", True, IF_MATCH_DOC)
        )
    plan_body(ir, method, arguments)
    plan_query(ir, method, arguments)
    plan_conditionals(method, arguments)
    plan_request_flags(method, arguments)
    plan_options(method, arguments)
    names = [a.name for a in arguments.positional + arguments.keywords]
    if len(set(names)) != len(names):
        raise GeneratorError(f"{method['operationId']}: argument names collide")

    returns, call, response_type, overloads = plan_return(ir, method)
    paged = call == "request_page"
    return MethodPlan(
        name=identifier(method["name"]),
        positional=arguments.positional,
        keywords=arguments.keywords,
        returns=returns,
        call=call,
        request=arguments.request,
        response_type=response_type,
        cursor_param=method["pagination"]["cursorParam"] if paged else None,
        position_field=position_field(ir, method) if paged else None,
        docs=[method["summary"], method["description"], RETURN_DOCS.get(call)],
        overloads=overloads,
    )


IF_MATCH_DOC = (
    "The ETag the object was read with, or the object itself (its "
    "`last_response.etag` is sent). A stale ETag raises "
    '`PreconditionFailedError`; `"*"` matches any version.'
)
IF_NONE_MATCH_DOC = (
    "The ETag of the copy the caller holds, or that copy itself. When it is "
    "still current the API answers 304 and the method returns `NotModified`."
)
STREAM_DOC = (
    "Return a stream (`BinaryStream`, or `AsyncBinaryStream` on the async "
    "client) as soon as the headers arrive instead of reading the whole file. "
    "Use it as a context manager so the connection is released."
)
IDEMPOTENCY_DOC = (
    "Overrides the key generated for this call. Retries reuse the same key."
)
MAX_RETRIES_DOC = "Overrides the client's `max_retries` for this call."
TIMEOUT_DOC = "Overrides the client's `timeout` for this call, in seconds."
REQUEST_ID_DOC = (
    "Sent as `x-request-id` on every attempt, so this call can be found in "
    "your logs and TeachMeHIPAA's. The API echoes it on `last_response` and "
    "on errors if it matches `^[A-Za-z0-9._-]{1,128}$`, and replaces it "
    "otherwise."
)
RETURN_DOCS = {
    "request_empty": "Returns `None`: the API answers 204 No Content.",
    "request_write_result": (
        "`created` is true when this call created the Learner (201) and false "
        "when it already existed (200)."
    ),
    "request_binary": (
        "Returns the file's bytes with its content type and filename, or with "
        "`stream=True` a stream to read them from."
    ),
}


# Classes that differ between the clients, written as these placeholders
# while planning and filled in per client.
CLIENT_CLASSES = {
    "{page}": ("SyncPage", "AsyncPage"),
    "{stream}": ("BinaryStream", "AsyncBinaryStream"),
    "{operation}": ("Operation", "AsyncOperation"),
}


def for_client(text: str, asynchronous: bool) -> str:
    for placeholder, (sync_name, async_name) in CLIENT_CLASSES.items():
        text = text.replace(placeholder, async_name if asynchronous else sync_name)
    return text


def render_signature(
    plan: MethodPlan,
    asynchronous: bool,
    returns: str,
    narrowed: Mapping[str, str],
) -> list[str]:
    returns = for_client(returns, asynchronous)
    parameters = ["self"]
    parameters += [a.signature() for a in plan.positional]
    if plan.positional:
        parameters.append("/")
    parameters.append("*")
    parameters += [narrowed.get(a.name, a.signature()) for a in plan.keywords]
    prefix = "async def" if asynchronous else "def"
    lines = [f"    {prefix} {plan.name}("]
    lines += [f"        {parameter}," for parameter in parameters]
    lines.append(f"    ) -> {returns}:")
    return lines


def render_method(plan: MethodPlan, asynchronous: bool) -> list[str]:
    lines: list[str] = []
    for variant in plan.overloads:
        lines.append("    @overload")
        lines += render_signature(
            plan, asynchronous, variant.returns, variant.arguments
        )
        lines[-1] += " ..."
        lines.append("")
    lines += render_signature(plan, asynchronous, plan.returns, {})
    described = [a for a in plan.positional + plan.keywords if a.description]
    args = "Args:\n" + "\n".join(f"    {a.name}: {a.description}" for a in described)
    lines += docstring([*plan.docs, args if described else None], 8)
    arguments = [f"ApiRequest({', '.join(plan.request)})"]
    if plan.response_type is not None:
        arguments.append(for_client(plan.response_type, asynchronous))
    if plan.cursor_param is not None:
        arguments.append(f"cursor_param={json.dumps(plan.cursor_param)}")
        if plan.position_field is not None:
            arguments.append(f"position_field={json.dumps(plan.position_field)}")
    awaiting = "await " if asynchronous else ""
    if plan.call == "request_binary":
        # The overloads tie the return type to `stream`.
        pipeline = f"{awaiting}self._pipeline"
        lines.append(f"        api_request = {arguments[0]}")
        lines.append("        if stream:")
        lines.append(
            f"            return {pipeline}.request_binary_stream(api_request)"
        )
        lines.append(f"        return {pipeline}.request_binary(api_request)")
        return lines
    call = f"{awaiting}self._pipeline.{plan.call}({', '.join(arguments)})"
    if plan.call == "request_operation":
        # Operations live outside `_core`: they subclass a generated model.
        function = f"{'async_' if asynchronous else ''}request_operation"
        call = f"{awaiting}{function}(self._pipeline, {', '.join(arguments)})"
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
        if path not in EXTENSION_DOCS:
            raise GeneratorError(f"extended resource {path} needs EXTENSION_DOCS")
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
        "from typing import Literal, overload",
        "",
        "import httpx",
        "from pydantic import TypeAdapter",
        "",
        "from .._core._files import FileInput",
        "from .._core._models import (",
        "    AsyncBinaryStream,",
        "    BinaryResponse,",
        "    BinaryStream,",
        "    ETagSource,",
        "    NotModified,",
        ")",
        "from .._core._pagination import AsyncPage, SyncPage",
        "from .._core._pipeline import AsyncPipeline, SyncPipeline",
        "from .._core._request import ApiRequest, RequestOptions, with_fixed",
        "from .._core._resource import AsyncAPIResource, SyncAPIResource",
        "from .._core._sentinel import NOT_GIVEN, NotGiven",
        "from .._operations import (",
        "    AsyncOperation,",
        "    Operation,",
        "    WebhookDeliveryResult,",
        "    async_request_operation,",
        "    request_operation,",
        ")",
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


# --- the Markdown reference ----------------------------------------------------

REFERENCE_BANNER = (
    "<!-- Generated from openapi/sdk-ir.json by scripts/generate.py — do not edit. -->"
)
# Every method takes these; the reference says so once instead of per method.
CALL_OPTIONS = frozenset({"max_retries", "timeout", "request_id"})


def reference_argument(argument: Argument) -> str:
    null = " | None" if argument.nullable else ""
    if argument.default is not None:
        return f"{argument.name}: {argument.annotation}{null} = {argument.default}"
    optional = "" if argument.required else " = ..."
    return f"{argument.name}: {argument.annotation}{null}{optional}"


def reference_signature(path: str, plan: MethodPlan) -> str:
    """The sync call as a caller writes it, wrapped like `ruff format`
    would wrap a definition once it passes the line length."""
    parameters = [reference_argument(a) for a in plan.positional]
    if plan.positional:
        parameters.append("/")
    keywords = [a for a in plan.keywords if a.name not in CALL_OPTIONS]
    if keywords:
        parameters.append("*")
        parameters += [reference_argument(a) for a in keywords]
    returns = for_client(plan.returns, asynchronous=False)
    call = f"client.{path}.{plan.name}"
    one_line = f"{call}({', '.join(parameters)}) -> {returns}"
    if len(one_line) <= LINE_LENGTH:
        return one_line
    return "\n".join(
        [f"{call}(", *[f"    {p}," for p in parameters], f") -> {returns}"]
    )


def reference_scopes(method: Json) -> str:
    security = method["security"]
    if security["kind"] == "none":
        return "none (public: the client sends no Access token)"
    alternatives = [
        " and ".join(f"`{s}`" for s in group) for group in security["anyOf"]
    ]
    if alternatives == [""]:
        return "any Access token"
    return " or ".join(alternatives)


def reference_notes(method: Json, plan: MethodPlan) -> list[str]:
    notes = []
    if method["idempotencyKey"] != "none":
        notes.append(
            "Sends a generated `Idempotency-Key` that its retries reuse; pass "
            "`idempotency_key=` to choose your own."
        )
    if method["retrySafe"]:
        notes.append("Retried after network errors, 409 `conflict`, 429 and 5xx.")
    else:
        notes.append("Never retried, since a replay could repeat the change.")
    if method["ifMatch"] == "required":
        notes.append(
            "Requires `if_match=` (an ETag or the model you read); a stale "
            "one raises `PreconditionFailedError`."
        )
    elif method["ifMatch"] == "optional":
        notes.append("Pass `if_match=` to make the call fail if the object changed.")
    if method["ifNoneMatch"] != "none":
        notes.append(
            "Pass `if_none_match=` to get `NotModified` back when your copy is current."
        )
    if plan.call == "request_page":
        notes.append("Loop over the page with `for` to get items from every page.")
    if plan.call == "request_operation":
        notes.append("Returns an Operation; `wait()` returns it once it's done.")
    if plan.call == "request_binary":
        notes.append("Pass `stream=True` to read the file in chunks as it arrives.")
    if method["requestBody"] is not None and (
        method["requestBody"]["contentType"] == "application/merge-patch+json"
    ):
        notes.append(
            "A merge patch: fields you leave out keep their value, `None` clears one."
        )
    return notes


def reference_method(ir: Ir, path: tuple[str, ...], method: Json) -> list[str]:
    plan = plan_method(ir, method)
    dotted = ".".join(identifier(part) for part in path)
    http = f"{method['httpMethod']} {request_path(method)}"
    lines = [
        f"### `{dotted}.{plan.name}`",
        "",
        "```python",
        reference_signature(dotted, plan),
        "```",
        "",
        f"`{http}`",
        "",
        str(method["summary"]).rstrip(".") + ".",
    ]
    if method["description"]:
        lines += ["", str(method["description"])]
    lines += [
        "",
        f"- **Scopes:** {reference_scopes(method)}",
        f"- **Returns:** `{for_client(plan.returns, asynchronous=False)}`",
        *[f"- {note}" for note in reference_notes(method, plan)],
    ]
    return lines


def reference_events(ir: Ir) -> list[str]:
    envelope = ir.types[ir.event_envelope]
    mapping = envelope["discriminator"]["mapping"]
    catalog = {entry["type"]: entry["data"] for entry in ir.raw["events"]["catalog"]}
    lines = [
        "## Event types",
        "",
        "`events.list`, `events.tail` and `Webhook.construct_event` give you "
        "one of these models per Event. An Event type this version doesn't "
        f"know arrives as `{ir.unknown_event}`.",
        "",
        "| Event type | Model | `data` |",
        "| --- | --- | --- |",
    ]
    for event_type in sorted(mapping):
        data = model_type(catalog[event_type])
        lines.append(f"| `{event_type}` | `{mapping[event_type]}` | `{data}` |")
    return lines


def render_reference(ir: Ir) -> str:
    roots = resource_tree(ir)
    nodes = [node for _, root in sorted(roots.items()) for node in root.walk()]
    lines = [
        REFERENCE_BANNER,
        "",
        "# Resource reference",
        "",
        f"Every resource and method on the client, generated from the SDK IR "
        f"for Developer API document release `{ir.raw['source']['release']}`. "
        "`code-samples.json`, next to this file, holds a runnable sample for "
        "each operation.",
        "",
        "Each signature is written for the sync `TeachMeHipaa` client. On "
        "`AsyncTeachMeHipaa` you `await` the same method and get `AsyncPage`, "
        "`AsyncOperation` or `AsyncBinaryStream` where the sync client returns "
        "`SyncPage`, `Operation` or `BinaryStream` (see "
        "[Async support](../guides/async.md)). Path ids go first, positionally; "
        "every other argument is keyword-only. An argument shown as `= ...` is "
        "optional, and the client leaves it out of the request when you do. On "
        "top of the arguments listed, every method takes `max_retries`, "
        "`timeout` and `request_id` (see "
        "[Retries and timeouts](../guides/retries-and-timeouts.md)). Import "
        "model and parameter types from `teachmehipaa.types`.",
        "",
        "You never pass `{orgId}`: the client fills it in from the Organization "
        "its credentials belong to.",
        "",
        "## Resources",
        "",
    ]
    for node in nodes:
        dotted = ".".join(identifier(part) for part in node.path)
        # GitHub's heading anchors drop dots and backticks but keep
        # underscores.
        anchor = dotted.replace(".", "")
        names = ", ".join(
            f"[`{identifier(m['name'])}`](#{anchor}{identifier(m['name'])})"
            for m in sorted(node.methods, key=lambda m: identifier(m["name"]))
        )
        lines.append(f"- [`{dotted}`](#{anchor}): {names}")
    for node in nodes:
        dotted = ".".join(identifier(part) for part in node.path)
        class_name = node.class_name
        lines += [
            "",
            f"## {dotted}",
            "",
            f"`client.{dotted}` is a `{class_name}` (`Async{class_name}` on "
            "the async client).",
        ]
        if is_extended(node):
            lines += ["", EXTENSION_DOCS[".".join(node.path)]]
        for method in sorted(node.methods, key=lambda m: identifier(m["name"])):
            lines += ["", *reference_method(ir, node.path, method)]
    lines += ["", *reference_events(ir)]
    return "\n".join(lines) + "\n"


# --- API reference code samples ----------------------------------------------

# One Python sample per operation for the API reference's language picker.
# The six SDKs use the same example values so their samples line up.
PATH_EXAMPLES = {
    "certId": "cert_01JD8F3G5H7J9K1M3N5P7Q9R1S",
    "courseId": "hipaa-2026",
    "enrollmentId": "enr_01JD8K2M4N6P8Q0R2S4T6V8W0X",
    "externalId": "hr-1042",
    "learnerId": "sub_01JD80AB2C3D4E5F6G7H8J9K0M",
    "operationId": "op_01JD8T4V6W8X0Y2Z4A6B8C0D2E",
    "subjectId": "sub_01JD80AB2C3D4E5F6G7H8J9K0M",
    "subscriptionId": "whs_01JD8Q5R7S9T1V3W5X7Y9Z1A3B",
    "tinyId": "a7Kq2Z",
}
# Python source for required keyword arguments, by argument name. A required
# argument with no value here or in the operation's `SampleSpec.keywords`
# stops the generator, so a new required field gets a sample value.
KEYWORD_EXAMPLES = {
    "email": '"dana.whitfield@example.com"',
    "endpoint_url": '"https://example.com/webhooks/teachmehipaa"',
    "event_types": '["learner.certified"]',
    "file": '"roster.csv"',
    "format": '"csv"',
    "items": '[{"email": "dana.whitfield@example.com", "name": "Dana Whitfield"}]',
    "operation": '"remind"',
    "select": '{"enrollment_ids": ["enr_01JD8K2M4N6P8Q0R2S4T6V8W0X"]}',
}
LEARNER = f'"{PATH_EXAMPLES["learnerId"]}"'
SUBSCRIPTION = f'"{PATH_EXAMPLES["subscriptionId"]}"'


@dataclass(frozen=True)
class SampleSpec:
    """How one operation's sample uses its method.

    `body` is the code after the client is built; `{call}` in it becomes the
    method call with the example values. `keywords` adds optional keyword
    arguments (at most one telling one) or overrides a required one's value.
    """

    body: str
    keywords: Mapping[str, str] = field(default_factory=dict)
    imports: tuple[str, ...] = ()


PATHLIB = ("from pathlib import Path",)

SAMPLES = {
    "listAuditEvents": SampleSpec(
        "for event in {call}:\n    print(event.type)",
        {"type": '"enrollment.transition"'},
    ),
    "introspectAccessToken": SampleSpec(
        "token = {call}\nprint(token.org_id, token.scopes)"
    ),
    "getCertificateVerification": SampleSpec(
        "verification = {call}\nprint(verification.status, verification.learner_name)"
    ),
    "downloadCertificatePdf": SampleSpec(
        "pdf = {call}\n"
        'Path(pdf.filename or "certificate.pdf").write_bytes(pdf.content)',
        imports=PATHLIB,
    ),
    "exportCertificates": SampleSpec(
        "export = {call}.wait().export_result()\n"
        'Path("certificates.csv").write_text(export.csv, newline="")',
        imports=PATHLIB,
    ),
    "listCertificates": SampleSpec(
        "for certificate in {call}:\n"
        "    print(certificate.certificate_id, certificate.expires_at)",
        {"subject_id": LEARNER},
    ),
    "getCertificate": SampleSpec(
        "certificate = {call}\nprint(certificate.status, certificate.expires_at)"
    ),
    "getCertificateCredentials": SampleSpec(
        "links = {call}\nprint(links.short_link, links.linked_in_url)"
    ),
    "getComplianceSummary": SampleSpec(
        'summary = {call}\nprint(f"{{summary.compliant_rate:.0%}} compliant")',
        {"course_id": '"hipaa-2026"'},
    ),
    "listCourses": SampleSpec(
        "for course in {call}:\n    print(course.course_id, course.title)"
    ),
    "getCourse": SampleSpec(
        "course = {call}\nprint(course.title, course.course_version)"
    ),
    "batchEnrollments": SampleSpec(
        "batch = {call}\n"
        "for result in batch.results:\n"
        "    print(result.enrollment_id, result.outcome)"
    ),
    "cancelEnrollment": SampleSpec("enrollment = {call}\nprint(enrollment.status)"),
    "createEnrollment": SampleSpec(
        "enrollment = {call}\nprint(enrollment.enrollment_id, enrollment.status)",
        {"course_id": '"hipaa-2026"'},
    ),
    "exportEnrollments": SampleSpec(
        "export = {call}.wait().export_result()\n"
        'Path("enrollments.csv").write_text(export.csv, newline="")',
        imports=PATHLIB,
    ),
    "importEnrollments": SampleSpec(
        "operation = {call}\nprint(operation.wait().response)",
        {"options": '{"course_id": "hipaa-2026"}'},
    ),
    "listEnrollments": SampleSpec(
        "for enrollment in {call}:\n"
        "    print(enrollment.enrollment_id, enrollment.certified_at)",
        {"status": '"CERTIFIED"'},
    ),
    "remindEnrollment": SampleSpec("accepted = {call}\nprint(accepted.action)"),
    "renewEnrollment": SampleSpec(
        "enrollment = {call}\nprint(enrollment.cycle, enrollment.status)"
    ),
    "resendEnrollmentInvite": SampleSpec("accepted = {call}\nprint(accepted.action)"),
    "getEnrollment": SampleSpec(
        "enrollment = {call}\nprint(enrollment.status, enrollment.expires_at)"
    ),
    "listOrgEvents": SampleSpec(
        "for event in {call}:\n    print(event.event_id, event.occurred_at)",
        {"type": '"learner.certified"'},
    ),
    "batchUpsertLearners": SampleSpec(
        "operation = {call}\nprint(operation.wait().response)"
    ),
    "createLearner": SampleSpec(
        "learner = {call}\nprint(learner.learner_id, learner.created)",
        {"name": '"Dana Whitfield"'},
    ),
    "createLearnerLaunchLink": SampleSpec(
        "link = {call}\nprint(link.url, link.expires_at)",
        {"course_id": '"hipaa-2026"'},
    ),
    "exportLearners": SampleSpec(
        "export = {call}.wait().export_result()\n"
        'Path("learners.csv").write_text(export.csv, newline="")',
        imports=PATHLIB,
    ),
    "listLearners": SampleSpec(
        "for learner in {call}:\n    print(learner.email, learner.status)",
        {"status": '"in_progress"'},
    ),
    "offboardLearner": SampleSpec("learner = {call}\nprint(learner.status)"),
    "remindLearner": SampleSpec("accepted = {call}\nprint(accepted.action)"),
    "getLearner": SampleSpec("learner = {call}\nprint(learner.name, learner.status)"),
    "updateLearner": SampleSpec(
        f"learner = client.learners.retrieve({LEARNER})\n"
        "updated = {call}\nprint(updated.name)",
        {"if_match": "learner", "name": '"Dana Whitfield"'},
    ),
    "upsertLearnerByExternalId": SampleSpec(
        "learner = {call}\nprint(learner.learner_id, learner.created)",
        {"name": '"Dana Whitfield"'},
    ),
    "listMembers": SampleSpec(
        "for member in {call}:\n    print(member.email, member.role)"
    ),
    "getMember": SampleSpec("member = {call}\nprint(member.email, member.role)"),
    "getOperation": SampleSpec(
        "operation = {call}\nprint(operation.name, operation.done)"
    ),
    "getSeatInventory": SampleSpec(
        'seats = {call}\nprint(seats.available, "of", seats.total, "seats available")'
    ),
    "createWebhookSubscription": SampleSpec(
        "subscription = {call}\n"
        "print(subscription.subscription_id, subscription.secret_key_id)"
    ),
    "deleteWebhookSubscription": SampleSpec('{call}\nprint("deleted")'),
    "listWebhookSubscriptions": SampleSpec(
        "for subscription in {call}:\n"
        "    print(subscription.subscription_id, subscription.endpoint_url)"
    ),
    "redriveWebhookSubscription": SampleSpec(
        "operation = {call}\nprint(operation.wait().response)"
    ),
    "getWebhookSubscription": SampleSpec(
        "subscription = {call}\n"
        "print(subscription.endpoint_url, subscription.event_types)"
    ),
    "testWebhookSubscription": SampleSpec(
        "operation = {call}\nprint(operation.wait(timeout=60).response)"
    ),
    "updateWebhookSubscription": SampleSpec(
        f"subscription = client.webhook_subscriptions.retrieve({SUBSCRIPTION})\n"
        "updated = {call}\nprint(updated.enabled)",
        {"if_match": "subscription", "enabled": "False"},
    ),
}

CLIENT_WITH_CREDENTIALS = """\
import os

from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(
    client_id=os.environ["TMH_CLIENT_ID"],
    client_secret=os.environ["TMH_CLIENT_SECRET"],
    environment="sandbox",
)
"""
# Public methods send no Access token, so their client takes no credentials.
CLIENT_WITHOUT_CREDENTIALS = """\
from teachmehipaa import TeachMeHipaa

client = TeachMeHipaa(environment="sandbox")
"""


def sample_call(ir: Ir, path: tuple[str, ...], method: Json, spec: SampleSpec) -> str:
    operation = method["operationId"]
    plan = plan_method(ir, method)
    arguments = []
    for p in method["pathParams"]:
        if p["name"] not in PATH_EXAMPLES:
            raise GeneratorError(f"{operation}: no sample value for {p['name']}")
        arguments.append(json.dumps(PATH_EXAMPLES[p["name"]]))
    keywords = {a.name: a for a in plan.keywords}
    unknown = sorted(set(spec.keywords) - set(keywords))
    if unknown:
        raise GeneratorError(f"{operation}: sample passes unknown {unknown}")
    for argument in plan.keywords:
        value = spec.keywords.get(argument.name)
        if value is None and argument.required:
            value = KEYWORD_EXAMPLES.get(argument.name)
            if value is None:
                raise GeneratorError(
                    f"{operation}: no sample value for {argument.name}"
                )
        if value is not None:
            arguments.append(f"{argument.name}={value}")
    dotted = ".".join(identifier(part) for part in path)
    return f"client.{dotted}.{plan.name}({', '.join(arguments)})"


def render_samples(ir: Ir) -> dict[str, str]:
    """operationId -> sample source, before formatting. Where two methods
    share an operationId, the sample shows the first (`enrollments.batch`,
    `enrollments.import_`)."""
    first: dict[str, tuple[tuple[str, ...], Json]] = {}
    for path, method in ir.methods:
        first.setdefault(method["operationId"], (path, method))
    if set(first) != set(SAMPLES):
        missing = sorted(set(first) - set(SAMPLES))
        extra = sorted(set(SAMPLES) - set(first))
        raise GeneratorError(f"samples missing for {missing}, unknown {extra}")
    samples = {}
    for operation, (path, method) in sorted(first.items()):
        spec = SAMPLES[operation]
        public = method["security"]["kind"] == "none"
        client = CLIENT_WITHOUT_CREDENTIALS if public else CLIENT_WITH_CREDENTIALS
        body = spec.body.format(call=sample_call(ir, path, method, spec))
        imports = "".join(f"{line}\n" for line in spec.imports)
        samples[operation] = f"{imports}{client}\n{body}\n"
    return samples


def render_code_samples(samples: Mapping[str, str]) -> str:
    """The `code-samples.json` the monorepo's API reference vendors."""
    document = {
        "language": "python",
        "release": OPENAPI_VERSION.read_text().strip(),
        "samples": dict(sorted(samples.items())),
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


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
        ir = load_ir()
        files = generate(ir)
        reference = render_reference(ir)
        samples = render_samples(ir)
    except GeneratorError as error:
        print(f"generate.py: {error}", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as scratch:
        out = Path(scratch)
        write_formatted(
            {
                **files,
                **{f"{SAMPLES_DIR}/{op}.py": code for op, code in samples.items()},
            },
            out,
        )
        fresh = generated_files(out)
        code_samples = render_code_samples(
            {op: (out / SAMPLES_DIR / f"{op}.py").read_text() for op in samples}
        )
    current = generated_files(PACKAGE)
    if arguments.check:
        stale = sorted(set(fresh) ^ set(current)) + sorted(
            name for name in fresh if current.get(name) != fresh[name]
        )
        diffs = [
            (f"src/teachmehipaa/{name}", current.get(name, ""), fresh.get(name, ""))
            for name in stale
        ]
        stale_documents = False
        for document, contents in (
            (REFERENCE, reference),
            (CODE_SAMPLES, code_samples),
        ):
            committed = document.read_text() if document.is_file() else ""
            stale_documents |= committed != contents
            diffs.append((str(document.relative_to(ROOT)), committed, contents))
        for path, old, new in diffs:
            sys.stdout.writelines(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    f"a/{path}",
                    f"b/{path}",
                )
            )
        return 1 if stale or stale_documents else 0
    for name in GENERATED_DIRS:
        shutil.rmtree(PACKAGE / name)
    for name, contents in fresh.items():
        target = PACKAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
    REFERENCE.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE.write_text(reference)
    CODE_SAMPLES.write_text(code_samples)
    return 0


if __name__ == "__main__":
    sys.exit(main())
