"""Generated surface coverage: every operation in the vendored spec maps to
exactly one public method, with the same name, on both clients."""

import hashlib
import inspect
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from teachmehipaa import NOT_GIVEN, AsyncTeachMeHipaa, TeachMeHipaa
from teachmehipaa._core._resource import AsyncAPIResource, SyncAPIResource
from tests.fake_api import CLIENT_ID, CLIENT_SECRET

OPENAPI = Path(__file__).parent.parent / "openapi"

# From api-sdk-surface.md §11, with the grilling's renames applied (Q12: the
# glossary bans "credential", so `retrieveLinks`; IR: `delete`, not `del`, and
# `auth.introspect`) and Q25's splits. `import` is a Python keyword, so the
# method carries PEP 8's trailing underscore.
EXPECTED_METHODS: dict[str, list[str]] = {
    "listAuditEvents": ["audit_events.list"],
    "introspectAccessToken": ["auth.introspect"],
    "getCertificateVerification": ["certificate_verifications.retrieve"],
    "downloadCertificatePdf": ["certificates.download_pdf"],
    "exportCertificates": ["certificates.export"],
    "listCertificates": ["certificates.list"],
    "getCertificate": ["certificates.retrieve"],
    "getCertificateCredentials": ["certificates.retrieve_links"],
    "getComplianceSummary": ["compliance.retrieve"],
    "listCourses": ["courses.list"],
    "getCourse": ["courses.retrieve"],
    "batchEnrollments": ["enrollments.batch", "enrollments.batch_by_filter"],
    "cancelEnrollment": ["enrollments.cancel"],
    "createEnrollment": ["enrollments.create"],
    "exportEnrollments": ["enrollments.export"],
    "importEnrollments": ["enrollments.import_", "enrollments.preview_import"],
    "listEnrollments": ["enrollments.list"],
    "remindEnrollment": ["enrollments.remind"],
    "renewEnrollment": ["enrollments.renew"],
    "resendEnrollmentInvite": ["enrollments.resend_invite"],
    "getEnrollment": ["enrollments.retrieve"],
    "listOrgEvents": ["events.list"],
    "batchUpsertLearners": ["learners.batch_upsert"],
    "createLearner": ["learners.create"],
    "createLearnerLaunchLink": ["learners.create_launch_link"],
    "exportLearners": ["learners.export"],
    "listLearners": ["learners.list"],
    "offboardLearner": ["learners.offboard"],
    "remindLearner": ["learners.remind"],
    "getLearner": ["learners.retrieve"],
    "updateLearner": ["learners.update"],
    "upsertLearnerByExternalId": ["learners.upsert_by_external_id"],
    "listMembers": ["members.list"],
    "getMember": ["members.retrieve"],
    "getOperation": ["operations.retrieve"],
    "getSeatInventory": ["seats.retrieve"],
    "createWebhookSubscription": ["webhook_subscriptions.create"],
    "deleteWebhookSubscription": ["webhook_subscriptions.delete"],
    "listWebhookSubscriptions": ["webhook_subscriptions.list"],
    "redriveWebhookSubscription": ["webhook_subscriptions.redrive"],
    "getWebhookSubscription": ["webhook_subscriptions.retrieve"],
    "testWebhookSubscription": ["webhook_subscriptions.test"],
    "updateWebhookSubscription": ["webhook_subscriptions.update"],
}

# The token endpoint is the hand-written auth layer, not a resource method.
HAND_WRITTEN = {"createAccessToken"}

# Public methods with no operation of their own, from `_extensions/`:
# `events.tail` iterates `listOrgEvents` (grilling Q22).
HAND_WRITTEN_METHODS = ["events.tail"]

EXPECTED_NAMES = sorted(name for names in EXPECTED_METHODS.values() for name in names)


def load(name: str) -> Any:
    return json.loads((OPENAPI / name).read_text())


def ir_methods() -> Iterator[tuple[str, Any]]:
    """(operationId, IR method) for every IR method."""
    for resource in load("sdk-ir.json")["resources"]:
        for method in resource["methods"]:
            yield method["operationId"], method


def ir_method_names() -> Iterator[tuple[str, str, str]]:
    """(operationId, IR resource path, IR method name) for every IR method."""
    for resource in load("sdk-ir.json")["resources"]:
        for method in resource["methods"]:
            yield method["operationId"], ".".join(resource["path"]), method["name"]


def resource_methods(resource: object, prefix: str) -> Iterator[str]:
    """Every public method of a resource and its sub-resources, dotted,
    including those a hand-written subclass adds to a generated class."""
    classes = type(resource).__mro__
    resource_classes = classes[: classes.index(_resource_base(resource))]
    names = {
        name
        for cls in resource_classes
        for name, value in vars(cls).items()
        if not name.startswith("_") and inspect.isfunction(value)
    }
    for name in sorted(names):
        yield prefix + name
    yield from sub_resource_methods(resource, prefix)


def _resource_base(resource: object) -> type:
    return (
        AsyncAPIResource if isinstance(resource, AsyncAPIResource) else SyncAPIResource
    )


def sub_resource_methods(namespace: object, prefix: str = "") -> Iterator[str]:
    for name, value in vars(namespace).items():
        if not name.startswith("_") and hasattr(value, "_pipeline"):
            yield from resource_methods(value, f"{prefix}{name}.")


def resolve(client: object, dotted: str) -> Any:
    target: Any = client
    for part in dotted.split("."):
        target = getattr(target, part)
    return target


def make_clients() -> tuple[TeachMeHipaa, AsyncTeachMeHipaa]:
    sync = TeachMeHipaa(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    async_ = AsyncTeachMeHipaa(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    return sync, async_


def test_the_vendored_ir_was_built_from_the_vendored_spec() -> None:
    source = load("sdk-ir.json")["source"]
    spec_bytes = (OPENAPI / "openapi.developer.json").read_bytes()
    version = (OPENAPI.parent / "OPENAPI_VERSION").read_text().strip()

    assert hashlib.sha256(spec_bytes).hexdigest() == source["sha256"]
    assert version == source["release"]


def test_every_spec_operation_except_the_token_endpoint_is_expected() -> None:
    spec = load("openapi.developer.json")
    operation_ids = {
        operation["operationId"]
        for path in spec["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    }

    assert len(operation_ids) == 44
    assert operation_ids - HAND_WRITTEN == set(EXPECTED_METHODS)


def test_every_ir_method_has_its_expected_name() -> None:
    ir = sorted(ir_method_names())

    assert {operation_id for operation_id, _, _ in ir} == set(EXPECTED_METHODS)
    for operation_id, resource, method in ir:
        # The IR names in camelCase; Python names in snake_case, so compare
        # with case and underscores folded.
        folded = f"{resource}.{method}".lower()
        assert folded in {
            name.replace("_", "").lower() for name in EXPECTED_METHODS[operation_id]
        }, operation_id


@pytest.mark.parametrize("client", list(make_clients()), ids=["sync", "async"])
def test_the_client_exposes_exactly_the_expected_methods_plus_hand_written_ones(
    client: object,
) -> None:
    assert sorted(sub_resource_methods(client)) == sorted(
        EXPECTED_NAMES + HAND_WRITTEN_METHODS
    )


def test_async_methods_are_coroutines_and_sync_methods_are_not() -> None:
    sync, async_ = make_clients()

    for name in EXPECTED_NAMES:
        assert not inspect.iscoroutinefunction(resolve(sync, name)), name
        assert inspect.iscoroutinefunction(resolve(async_, name)), name


def test_sync_and_async_methods_take_the_same_parameters() -> None:
    sync, async_ = make_clients()

    for name in EXPECTED_NAMES + HAND_WRITTEN_METHODS:
        sync_signature = inspect.signature(resolve(sync, name))
        async_signature = inspect.signature(resolve(async_, name))
        assert list(sync_signature.parameters) == list(async_signature.parameters)


def test_org_scoped_methods_take_no_org_id() -> None:
    sync, _ = make_clients()

    for name in EXPECTED_NAMES:
        parameters = inspect.signature(resolve(sync, name)).parameters
        assert "org_id" not in parameters, name
        assert "organization_id" not in parameters, name


def test_path_params_are_positional_only_and_the_rest_keyword_only() -> None:
    sync, _ = make_clients()
    learners = inspect.signature(sync.learners.update).parameters

    assert [(name, parameter.kind.name) for name, parameter in learners.items()] == [
        ("learner_id", "POSITIONAL_ONLY"),
        ("if_match", "KEYWORD_ONLY"),
        ("name", "KEYWORD_ONLY"),
        ("external_id", "KEYWORD_ONLY"),
        ("course_id", "KEYWORD_ONLY"),
        ("max_retries", "KEYWORD_ONLY"),
        ("timeout", "KEYWORD_ONLY"),
        ("request_id", "KEYWORD_ONLY"),
    ]


@pytest.mark.parametrize("client", list(make_clients()), ids=["sync", "async"])
def test_no_method_the_ir_marks_unsafe_to_retry_takes_an_idempotency_key(
    client: object,
) -> None:
    # The API ignores Idempotency-Key on PATCH and DELETE, so offering one
    # would promise a safety the call doesn't have.
    unsafe = [
        (operation_id, method)
        for operation_id, method in ir_methods()
        if not method["retrySafe"]
    ]

    assert {method["httpMethod"] for _, method in unsafe} == {"PATCH", "DELETE"}
    for operation_id, _ in unsafe:
        for name in EXPECTED_METHODS[operation_id]:
            parameters = inspect.signature(resolve(client, name)).parameters
            assert "idempotency_key" not in parameters, name


@pytest.mark.parametrize("client", list(make_clients()), ids=["sync", "async"])
def test_every_method_takes_a_keyword_only_request_id(client: object) -> None:
    for name in EXPECTED_NAMES + HAND_WRITTEN_METHODS:
        parameter = inspect.signature(resolve(client, name)).parameters["request_id"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name
        assert parameter.default is NOT_GIVEN, name


@pytest.mark.parametrize("client", list(make_clients()), ids=["sync", "async"])
def test_every_method_summary_is_a_sentence(client: object) -> None:
    # PEP 257: the summary, the docstring's first paragraph, ends a sentence.
    for name in EXPECTED_NAMES + HAND_WRITTEN_METHODS:
        docstring = inspect.getdoc(resolve(client, name))
        assert docstring is not None, name
        summary = docstring.split("\n\n")[0]
        assert summary.endswith("."), name
