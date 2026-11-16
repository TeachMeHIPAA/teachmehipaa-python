<!-- Generated from openapi/sdk-ir.json by scripts/generate.py — do not edit. -->

# Resource reference

Every resource and method of the client, generated from the SDK IR of the Developer API document release `trimmed-2026-11-15`.

Signatures show the synchronous `TeachMeHipaa` client. `AsyncTeachMeHipaa` has the same methods, awaited, returning `AsyncPage`, `AsyncOperation` and `AsyncBinaryStream` in place of `SyncPage`, `Operation` and `BinaryStream`. Every method also takes `max_retries`, `timeout` and `request_id` (see [Errors and retries](../guides/errors-and-retries.md)). Arguments shown as `= ...` are optional and not sent when left out. Ids in the path are positional; everything else is a keyword. Model and parameter types are in `teachmehipaa.types`.

Organization-scoped paths contain `{orgId}`, which the client fills in from its Organization binding.

## Resources

- [`audit_events`](#audit_events): [`list`](#audit_eventslist)
- [`auth`](#auth): [`introspect`](#authintrospect)
- [`certificate_verifications`](#certificate_verifications): [`retrieve`](#certificate_verificationsretrieve)
- [`certificates`](#certificates): [`download_pdf`](#certificatesdownload_pdf), [`export`](#certificatesexport), [`list`](#certificateslist), [`retrieve`](#certificatesretrieve), [`retrieve_links`](#certificatesretrieve_links)
- [`compliance`](#compliance): [`retrieve`](#complianceretrieve)
- [`courses`](#courses): [`list`](#courseslist), [`retrieve`](#coursesretrieve)
- [`enrollments`](#enrollments): [`batch`](#enrollmentsbatch), [`batch_by_filter`](#enrollmentsbatch_by_filter), [`cancel`](#enrollmentscancel), [`create`](#enrollmentscreate), [`export`](#enrollmentsexport), [`import_`](#enrollmentsimport_), [`list`](#enrollmentslist), [`preview_import`](#enrollmentspreview_import), [`remind`](#enrollmentsremind), [`renew`](#enrollmentsrenew), [`resend_invite`](#enrollmentsresend_invite), [`retrieve`](#enrollmentsretrieve)
- [`events`](#events): [`list`](#eventslist)
- [`learners`](#learners): [`batch_upsert`](#learnersbatch_upsert), [`create`](#learnerscreate), [`create_launch_link`](#learnerscreate_launch_link), [`export`](#learnersexport), [`list`](#learnerslist), [`offboard`](#learnersoffboard), [`remind`](#learnersremind), [`retrieve`](#learnersretrieve), [`update`](#learnersupdate), [`upsert_by_external_id`](#learnersupsert_by_external_id)
- [`members`](#members): [`list`](#memberslist), [`retrieve`](#membersretrieve)
- [`operations`](#operations): [`retrieve`](#operationsretrieve)
- [`seats`](#seats): [`retrieve`](#seatsretrieve)
- [`webhook_subscriptions`](#webhook_subscriptions): [`create`](#webhook_subscriptionscreate), [`delete`](#webhook_subscriptionsdelete), [`list`](#webhook_subscriptionslist), [`redrive`](#webhook_subscriptionsredrive), [`retrieve`](#webhook_subscriptionsretrieve), [`test`](#webhook_subscriptionstest), [`update`](#webhook_subscriptionsupdate)

## audit_events

`client.audit_events`: `AuditEvents`, or `AsyncAuditEvents` on the async client.

### `audit_events.list`

```python
client.audit_events.list(
    *,
    limit: int = ...,
    cursor: str = ...,
    type: ListAuditEventsType = ...,
    transition: ListAuditEventsTransition = ...,
    subject_id: str = ...,
    since: datetime = ...,
    until: datetime = ...,
) -> SyncPage[AuditEvent]
```

`GET /organizations/{orgId}/audit-events`

List all audit events.

Returns a list of the organization's audit events, newest first. Filter by `type`, `transition`, `subjectId`, or a `since` and `until` range.

- **Scopes:** `audit:read`
- **Returns:** `SyncPage[AuditEvent]`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Iterate the page for every item across pages.

## auth

`client.auth`: `Auth`, or `AsyncAuth` on the async client.

### `auth.introspect`

```python
client.auth.introspect() -> TokenIntrospection
```

`GET /auth/introspection`

Retrieve the current token.

Describes the access token you call with: whether it belongs to an API client or a person, its organization, its scopes and when it expires. Needs no scope.

- **Scopes:** any Access token
- **Returns:** `TokenIntrospection`
- Retried on network errors, 409 `conflict`, 429 and 5xx.

## certificate_verifications

`client.certificate_verifications`: `CertificateVerifications`, or `AsyncCertificateVerifications` on the async client.

### `certificate_verifications.retrieve`

```python
client.certificate_verifications.retrieve(tiny_id: str, /) -> CertificateVerification
```

`GET /certificate-verifications/{tinyId}`

Verify a certificate.

Verifies the certificate behind a `https://tme.so/{tinyId}` link. Needs no access token. Limited to 60 requests a minute per IP address.

- **Scopes:** none: a public method, sent without an Access token
- **Returns:** `CertificateVerification`
- Retried on network errors, 409 `conflict`, 429 and 5xx.

## certificates

`client.certificates`: `Certificates`, or `AsyncCertificates` on the async client.

### `certificates.download_pdf`

```python
client.certificates.download_pdf(
    cert_id: str,
    /,
    *,
    stream: bool = False,
) -> BinaryResponse | BinaryStream
```

`GET /organizations/{orgId}/certificates/{certId}/content`

Download a certificate.

Downloads the certificate as a PDF. Revoked and expired certificates are watermarked. Requires the `certificates:read` scope.

- **Scopes:** `certificates:read`
- **Returns:** `BinaryResponse | BinaryStream`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Pass `stream=True` to read the file as it arrives.

### `certificates.export`

```python
client.certificates.export(
    *,
    format: CertificatesExportRequestFormat,
    idempotency_key: str = ...,
) -> Operation
```

`POST /organizations/{orgId}/certificates:export`

Export certificates.

Exports the organization's certificate records as CSV. Requires the `certificates:read` scope.

- **Scopes:** `certificates:read`
- **Returns:** `Operation`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Returns an Operation: call `wait()` for the result.

### `certificates.list`

```python
client.certificates.list(
    *,
    limit: int = ...,
    cursor: str = ...,
    subject_id: str = ...,
) -> SyncPage[Certificate]
```

`GET /organizations/{orgId}/certificates`

List all certificates.

Returns a list of the organization's certificates. Pass `subjectId` to list one learner's.

- **Scopes:** `certificates:read`
- **Returns:** `SyncPage[Certificate]`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Iterate the page for every item across pages.

### `certificates.retrieve`

```python
client.certificates.retrieve(cert_id: str, /) -> Certificate
```

`GET /organizations/{orgId}/certificates/{certId}`

Retrieve a certificate.

Retrieves a certificate.

- **Scopes:** `certificates:read`
- **Returns:** `Certificate`
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `certificates.retrieve_links`

```python
client.certificates.retrieve_links(cert_id: str, /) -> CertificateLinks
```

`GET /organizations/{orgId}/certificates/{certId}/credentials`

Retrieve certificate links.

Retrieves the certificate's LinkedIn add-to-profile link and its public `tme.so` verification link. Requires the `certificates:read` scope.

- **Scopes:** `certificates:read`
- **Returns:** `CertificateLinks`
- Retried on network errors, 409 `conflict`, 429 and 5xx.

## compliance

`client.compliance`: `Compliance`, or `AsyncCompliance` on the async client.

### `compliance.retrieve`

```python
client.compliance.retrieve(*, course_id: str = ...) -> ComplianceSummary
```

`GET /organizations/{orgId}/compliance`

Retrieve the compliance summary.

Counts the organization's learners in one course by status. Removed learners aren't counted.

- **Scopes:** `compliance:read`
- **Returns:** `ComplianceSummary`
- Retried on network errors, 409 `conflict`, 429 and 5xx.

## courses

`client.courses`: `Courses`, or `AsyncCourses` on the async client.

### `courses.list`

```python
client.courses.list(*, limit: int = ..., cursor: str = ...) -> SyncPage[Course]
```

`GET /courses`

List all courses.

Returns a list of the courses in the public catalog. Needs no access token.

- **Scopes:** none: a public method, sent without an Access token
- **Returns:** `SyncPage[Course]`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Iterate the page for every item across pages.

### `courses.retrieve`

```python
client.courses.retrieve(
    course_id: str,
    /,
    *,
    if_none_match: ETagSource = ...,
) -> Course | NotModified
```

`GET /courses/{courseId}`

Retrieve a course.

Retrieves a course from the public catalog.

- **Scopes:** none: a public method, sent without an Access token
- **Returns:** `Course | NotModified`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Takes `if_none_match` and returns `NotModified` when your copy is current.

## enrollments

`client.enrollments`: `Enrollments`, or `AsyncEnrollments` on the async client.

### `enrollments.batch`

```python
client.enrollments.batch(
    *,
    operation: EnrollmentsBatchRequestOperation,
    select: EnrollmentsBatchRequestSelectEnrollmentIdsParam,
    idempotency_key: str = ...,
) -> EnrollmentsBatchResults
```

`POST /organizations/{orgId}/enrollments:batch`

Update many enrollments.

Reminds, resends, cancels, renews, archives or unarchives up to 500 enrollments in one request, chosen by id or by filter. Each enrollment succeeds or fails on its own. Requires the `enrollments:write` scope.

- **Scopes:** `enrollments:write`
- **Returns:** `EnrollmentsBatchResults`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `enrollments.batch_by_filter`

```python
client.enrollments.batch_by_filter(
    *,
    operation: EnrollmentsBatchRequestOperation,
    select: EnrollmentsBatchRequestSelectFilterParam,
    idempotency_key: str = ...,
) -> Operation
```

`POST /organizations/{orgId}/enrollments:batch`

Update many enrollments.

Reminds, resends, cancels, renews, archives or unarchives up to 500 enrollments in one request, chosen by id or by filter. Each enrollment succeeds or fails on its own. Requires the `enrollments:write` scope.

- **Scopes:** `enrollments:write`
- **Returns:** `Operation`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Returns an Operation: call `wait()` for the result.

### `enrollments.cancel`

```python
client.enrollments.cancel(
    enrollment_id: str,
    /,
    *,
    refund: bool = ...,
    idempotency_key: str = ...,
) -> CancelEnrollmentResponse
```

`POST /organizations/{orgId}/enrollments/{enrollmentId}:cancel`

Cancel an enrollment.

Cancels an invite that hasn't been accepted yet and returns its seat to the pool. With `refund: true`, refunds the seat to the card that paid for it instead. The enrollment remains, with status `CANCELLED`. Requires the `enrollments:write` scope.

- **Scopes:** `enrollments:write`
- **Returns:** `CancelEnrollmentResponse`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `enrollments.create`

```python
client.enrollments.create(
    *,
    email: str,
    name: str = ...,
    course_id: str = ...,
    idempotency_key: str = ...,
) -> Enrollment
```

`POST /organizations/{orgId}/enrollments`

Create an enrollment.

Invites a person to a course, creating their profile if needed, and uses one seat. The course defaults to `hipaa`. Requires the `enrollments:write` scope.

- **Scopes:** `enrollments:write`
- **Returns:** `Enrollment`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `enrollments.export`

```python
client.enrollments.export(
    *,
    format: EnrollmentsExportRequestFormat,
    idempotency_key: str = ...,
) -> Operation
```

`POST /organizations/{orgId}/enrollments:export`

Export enrollments.

Exports the organization's enrollments as CSV. Requires the `enrollments:read` scope.

- **Scopes:** `enrollments:read`
- **Returns:** `Operation`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Returns an Operation: call `wait()` for the result.

### `enrollments.import_`

```python
client.enrollments.import_(
    *,
    file: FileInput,
    options: ImportOptionsParam = ...,
    idempotency_key: str = ...,
) -> Operation
```

`POST /organizations/{orgId}/enrollments:import`

Import learners from CSV.

Invites everyone in a CSV file with an `email` column (and optional `name` and `courseId`). Send `validateOnly: true` first to preview the file without inviting anyone. Up to 500 rows. Requires the `enrollments:write` scope.

- **Scopes:** `enrollments:write`
- **Returns:** `Operation`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Returns an Operation: call `wait()` for the result.

### `enrollments.list`

```python
client.enrollments.list(
    *,
    limit: int = ...,
    cursor: str = ...,
    status: ListEnrollmentsStatus = ...,
    course_id: str = ...,
    archived: ListEnrollmentsArchived = ...,
    include: ListEnrollmentsInclude = ...,
) -> SyncPage[OrgEnrollmentListItem]
```

`GET /organizations/{orgId}/enrollments`

List all enrollments.

Returns a list of the organization's enrollments. Filter by `status`, `courseId` or `archived`. Requires the `enrollments:read` scope.

- **Scopes:** `enrollments:read`
- **Returns:** `SyncPage[OrgEnrollmentListItem]`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Iterate the page for every item across pages.

### `enrollments.preview_import`

```python
client.enrollments.preview_import(
    *,
    file: FileInput,
    options: ImportOptionsParam = ...,
    idempotency_key: str = ...,
) -> ImportPreview
```

`POST /organizations/{orgId}/enrollments:import`

Import learners from CSV.

Invites everyone in a CSV file with an `email` column (and optional `name` and `courseId`). Send `validateOnly: true` first to preview the file without inviting anyone. Up to 500 rows. Requires the `enrollments:write` scope.

- **Scopes:** `enrollments:write`
- **Returns:** `ImportPreview`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `enrollments.remind`

```python
client.enrollments.remind(
    enrollment_id: str,
    /,
    *,
    idempotency_key: str = ...,
) -> EnrollmentActionAccepted
```

`POST /organizations/{orgId}/enrollments/{enrollmentId}:remind`

Remind an enrollment.

Emails the learner again: the invitation if they haven't joined, or a reminder linking to the training if they have. Requires the `enrollments:write` scope.

- **Scopes:** `enrollments:write`
- **Returns:** `EnrollmentActionAccepted`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `enrollments.renew`

```python
client.enrollments.renew(
    enrollment_id: str,
    /,
    *,
    idempotency_key: str = ...,
) -> Enrollment
```

`POST /organizations/{orgId}/enrollments/{enrollmentId}:renew`

Renew an enrollment.

Starts the next certification cycle for a certified learner and invites them again, using one seat. Retrying never uses a second seat. Requires the `enrollments:write` scope.

- **Scopes:** `enrollments:write`
- **Returns:** `Enrollment`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `enrollments.resend_invite`

```python
client.enrollments.resend_invite(
    enrollment_id: str,
    /,
    *,
    idempotency_key: str = ...,
) -> EnrollmentActionAccepted
```

`POST /organizations/{orgId}/enrollments/{enrollmentId}:resendInvite`

Resend an invite.

Sends a pending invite again, within the same cycle. To invite a certified learner again, renew the enrollment. Requires the `enrollments:write` scope.

- **Scopes:** `enrollments:write`
- **Returns:** `EnrollmentActionAccepted`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `enrollments.retrieve`

```python
client.enrollments.retrieve(
    enrollment_id: str,
    /,
    *,
    if_none_match: ETagSource = ...,
) -> Enrollment | NotModified
```

`GET /organizations/{orgId}/enrollments/{enrollmentId}`

Retrieve an enrollment.

Retrieves an enrollment. Requires the `enrollments:read` scope.

- **Scopes:** `enrollments:read`
- **Returns:** `Enrollment | NotModified`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Takes `if_none_match` and returns `NotModified` when your copy is current.

## events

`client.events`: `Events`, or `AsyncEvents` on the async client.

`client.events.tail(...)` is hand-written: it reads the Event log from a saved position, once or following new Events. See [Pagination and Events](../guides/pagination-and-events.md#tailing-the-event-log).

### `events.list`

```python
client.events.list(
    *,
    limit: int = ...,
    after: str = ...,
    type: EventType = ...,
) -> SyncPage[Event]
```

`GET /organizations/{orgId}/events`

List all events.

Returns a list of the organization's events from the last 30 days, oldest first. Pass the last `eventId` you processed as `after` to resume where you stopped, and `type` to list one event type.

- **Scopes:** `webhooks:manage` or `audit:read`
- **Returns:** `SyncPage[Event]`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Iterate the page for every item across pages.

## learners

`client.learners`: `Learners`, or `AsyncLearners` on the async client.

### `learners.batch_upsert`

```python
client.learners.batch_upsert(
    *,
    items: Sequence[LearnerBatchUpsertRequestItemsItemParam],
    delivery: LearnerBatchUpsertRequestDelivery = ...,
    seat_policy: LearnerBatchUpsertRequestSeatPolicy = ...,
    idempotency_key: str = ...,
) -> Operation
```

`POST /organizations/{orgId}/learners:batchUpsert`

Create many learners.

Creates or retrieves up to 500 learners in one request. Each item works like creating one learner and succeeds or fails on its own.

- **Scopes:** `learners:write`
- **Returns:** `Operation`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Returns an Operation: call `wait()` for the result.

### `learners.create`

```python
client.learners.create(
    *,
    email: str,
    name: str = ...,
    external_id: str = ...,
    course_id: str = ...,
    delivery: LearnerCreateRequestDelivery = ...,
    seat_policy: LearnerCreateRequestSeatPolicy = ...,
    idempotency_key: str = ...,
) -> LearnerWriteResult
```

`POST /organizations/{orgId}/learners`

Create a learner.

Adds a person to the organization and invites them to a course in one call, using one seat. If the email or `externalId` already belongs to an active learner in the course, nothing is created. With `delivery: "none"`, no email is sent and the response includes a `joinUrl` for you to deliver.

- **Scopes:** `learners:write`
- **Returns:** `LearnerWriteResult`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `learners.create_launch_link`

```python
client.learners.create_launch_link(
    learner_id: str,
    /,
    *,
    course_id: str = ...,
) -> LearnerLaunchLink
```

`POST /organizations/{orgId}/learners/{learnerId}:createLaunchLink`

Create a launch link.

Creates a link that opens the course with the learner already signed in, for a "Start training" button in your product. The link works once and expires after 5 minutes: create it when the learner clicks, then redirect them to it. Never email, store or log it. Only for a learner who has accepted their invite.

- **Scopes:** `learners:write`
- **Returns:** `LearnerLaunchLink`
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `learners.export`

```python
client.learners.export(
    *,
    format: LearnersExportRequestFormat,
    course_id: str = ...,
    status: LearnerStatus = ...,
    idempotency_key: str = ...,
) -> Operation
```

`POST /organizations/{orgId}/learners:export`

Export learners.

Exports the organization's learners in one course as CSV, optionally only those with one `status`. Requires the `learners:read` scope.

- **Scopes:** `learners:read`
- **Returns:** `Operation`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Returns an Operation: call `wait()` for the result.

### `learners.list`

```python
client.learners.list(
    *,
    limit: int = ...,
    cursor: str = ...,
    email: str = ...,
    external_id: str = ...,
    status: LearnerStatus = ...,
    course_id: str = ...,
) -> SyncPage[Learner]
```

`GET /organizations/{orgId}/learners`

List all learners.

Returns a list of the organization's learners in one course, with each learner's status, dates and current certificate. Filter by `status`, or find one learner by `email` or `externalId`.

- **Scopes:** `learners:read`
- **Returns:** `SyncPage[Learner]`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Iterate the page for every item across pages.

### `learners.offboard`

```python
client.learners.offboard(
    learner_id: str,
    /,
    *,
    course_id: str = ...,
    if_match: ETagSource = ...,
    idempotency_key: str = ...,
) -> Learner
```

`POST /organizations/{orgId}/learners/{learnerId}:offboard`

Offboard a learner.

Removes a learner from the organization. A learner who hasn't started has their invite cancelled and the seat returned; a learner who has started keeps their training history and certificates. Releases the learner's `externalId`.

- **Scopes:** `learners:write`
- **Returns:** `Learner`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Takes `if_match` to refuse the call if the object changed.

### `learners.remind`

```python
client.learners.remind(
    learner_id: str,
    /,
    *,
    course_id: str = ...,
    idempotency_key: str = ...,
) -> LearnerRemindAccepted
```

`POST /organizations/{orgId}/learners/{learnerId}:remind`

Remind a learner.

Emails the learner a reminder: the invite again if they haven't started, or a nudge to finish if they have.

- **Scopes:** `learners:write`
- **Returns:** `LearnerRemindAccepted`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `learners.retrieve`

```python
client.learners.retrieve(learner_id: str, /, *, course_id: str = ...) -> Learner
```

`GET /organizations/{orgId}/learners/{learnerId}`

Retrieve a learner.

Retrieves a learner's status in one course.

- **Scopes:** `learners:read`
- **Returns:** `Learner`
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `learners.update`

```python
client.learners.update(
    learner_id: str,
    /,
    *,
    if_match: ETagSource,
    name: str = ...,
    external_id: str | None = ...,
    course_id: str = ...,
) -> Learner
```

`PATCH /organizations/{orgId}/learners/{learnerId}`

Update a learner.

Updates a learner's `name` or `externalId`; parameters you don't send are left unchanged. Send the body as `application/merge-patch+json` with the learner's current `ETag` in `If-Match`.

- **Scopes:** `learners:write`
- **Returns:** `Learner`
- Never retried: it is not safe to replay.
- Requires `if_match` (an ETag or the object read); a stale one raises `PreconditionFailedError`.
- A merge patch: omitted arguments stay unchanged; `None` clears a field.

### `learners.upsert_by_external_id`

```python
client.learners.upsert_by_external_id(
    external_id: str,
    /,
    *,
    email: str,
    name: str = ...,
    course_id: str = ...,
    delivery: LearnerUpsertRequestDelivery = ...,
    seat_policy: LearnerUpsertRequestSeatPolicy = ...,
    idempotency_key: str = ...,
) -> LearnerWriteResult
```

`PUT /organizations/{orgId}/learners/by-external-id/{externalId}`

Create or retrieve a learner by your id.

Makes sure a learner exists for your own id. Creates and invites the learner the first time, and returns them on every later call, so a sync job can replay it safely. Never uses a second seat.

- **Scopes:** `learners:write`
- **Returns:** `LearnerWriteResult`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

## members

`client.members`: `Members`, or `AsyncMembers` on the async client.

### `members.list`

```python
client.members.list(
    *,
    limit: int = ...,
    cursor: str = ...,
    include: str = ...,
    role: ListMembersRole = ...,
) -> SyncPage[MemberListItem]
```

`GET /organizations/{orgId}/members`

List all members.

Returns a list of the organization's members, its admins and learners. Pass `role=admin` to list only admins.

- **Scopes:** `members:read`
- **Returns:** `SyncPage[MemberListItem]`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Iterate the page for every item across pages.

### `members.retrieve`

```python
client.members.retrieve(subject_id: str, /) -> Member
```

`GET /organizations/{orgId}/members/{subjectId}`

Retrieve a member.

Retrieves a member of the organization.

- **Scopes:** `members:read`
- **Returns:** `Member`
- Retried on network errors, 409 `conflict`, 429 and 5xx.

## operations

`client.operations`: `Operations`, or `AsyncOperations` on the async client.

### `operations.retrieve`

```python
client.operations.retrieve(operation_id: str, /) -> Operation
```

`GET /organizations/{orgId}/operations/{operationId}`

Retrieve an operation.

Retrieves a bulk operation and its result. Operations are kept for 24 hours.

- **Scopes:** any Access token
- **Returns:** `Operation`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Returns an Operation: call `wait()` for the result.

## seats

`client.seats`: `Seats`, or `AsyncSeats` on the async client.

### `seats.retrieve`

```python
client.seats.retrieve() -> SeatsInventory
```

`GET /organizations/{orgId}/seats`

Retrieve the seat inventory.

Retrieves how many seats the organization has, how many are assigned and how many are available for new invites. Requires the `enrollments:read` scope.

- **Scopes:** `enrollments:read`
- **Returns:** `SeatsInventory`
- Retried on network errors, 409 `conflict`, 429 and 5xx.

## webhook_subscriptions

`client.webhook_subscriptions`: `WebhookSubscriptions`, or `AsyncWebhookSubscriptions` on the async client.

### `webhook_subscriptions.create`

```python
client.webhook_subscriptions.create(
    *,
    endpoint_url: str,
    event_types: Sequence[EventType],
    description: str = ...,
    seats_low_threshold: int = ...,
    idempotency_key: str = ...,
) -> WebhookSubscriptionCreated
```

`POST /organizations/{orgId}/webhook-subscriptions`

Create a webhook subscription.

Subscribes an HTTPS endpoint to event types and creates its signing secret. Requires the `webhooks:manage` or `org:admin` scope.

- **Scopes:** `org:admin` or `webhooks:manage`
- **Returns:** `WebhookSubscriptionCreated`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.

### `webhook_subscriptions.delete`

```python
client.webhook_subscriptions.delete(subscription_id: str, /) -> None
```

`DELETE /organizations/{orgId}/webhook-subscriptions/{subscriptionId}`

Delete a webhook subscription.

Deletes a webhook subscription and its signing secret. Requires the `webhooks:manage` or `org:admin` scope.

- **Scopes:** `org:admin` or `webhooks:manage`
- **Returns:** `None`
- Never retried: it is not safe to replay.

### `webhook_subscriptions.list`

```python
client.webhook_subscriptions.list(
    *,
    limit: int = ...,
    cursor: str = ...,
) -> SyncPage[WebhookSubscription]
```

`GET /organizations/{orgId}/webhook-subscriptions`

List all webhook subscriptions.

Returns a list of the organization's webhook subscriptions. Signing secrets are never returned. Requires the `webhooks:manage` or `org:admin` scope.

- **Scopes:** `org:admin` or `webhooks:manage`
- **Returns:** `SyncPage[WebhookSubscription]`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Iterate the page for every item across pages.

### `webhook_subscriptions.redrive`

```python
client.webhook_subscriptions.redrive(
    subscription_id: str,
    /,
    *,
    idempotency_key: str = ...,
) -> Operation[WebhookDeliveryResult]
```

`POST /organizations/{orgId}/webhook-subscriptions/{subscriptionId}:redrive`

Retry failed deliveries.

Delivers the subscription's failed events again. Requires the `webhooks:manage` or `org:admin` scope.

- **Scopes:** `org:admin` or `webhooks:manage`
- **Returns:** `Operation[WebhookDeliveryResult]`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Returns an Operation: call `wait()` for the result.

### `webhook_subscriptions.retrieve`

```python
client.webhook_subscriptions.retrieve(
    subscription_id: str,
    /,
    *,
    if_none_match: ETagSource = ...,
) -> WebhookSubscription | NotModified
```

`GET /organizations/{orgId}/webhook-subscriptions/{subscriptionId}`

Retrieve a webhook subscription.

Retrieves a webhook subscription. Requires the `webhooks:manage` or `org:admin` scope.

- **Scopes:** `org:admin` or `webhooks:manage`
- **Returns:** `WebhookSubscription | NotModified`
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Takes `if_none_match` and returns `NotModified` when your copy is current.

### `webhook_subscriptions.test`

```python
client.webhook_subscriptions.test(
    subscription_id: str,
    /,
    *,
    idempotency_key: str = ...,
) -> Operation[WebhookDeliveryResult]
```

`POST /organizations/{orgId}/webhook-subscriptions/{subscriptionId}:test`

Send a test event.

Sends a signed test delivery to the subscription's endpoint, so you can check your verifier. Requires the `webhooks:manage` or `org:admin` scope.

- **Scopes:** `org:admin` or `webhooks:manage`
- **Returns:** `Operation[WebhookDeliveryResult]`
- Sends a generated `Idempotency-Key`, reused by its retries; pass `idempotency_key` to set your own.
- Retried on network errors, 409 `conflict`, 429 and 5xx.
- Returns an Operation: call `wait()` for the result.

### `webhook_subscriptions.update`

```python
client.webhook_subscriptions.update(
    subscription_id: str,
    /,
    *,
    if_match: ETagSource,
    endpoint_url: str = ...,
    event_types: Sequence[EventType] = ...,
    enabled: bool = ...,
    description: str | None = ...,
    seats_low_threshold: int = ...,
) -> WebhookSubscription
```

`PATCH /organizations/{orgId}/webhook-subscriptions/{subscriptionId}`

Update a webhook subscription.

Updates a webhook subscription; parameters you don't send are left unchanged. Send its current `ETag` in `If-Match`. The signing secret doesn't change. Requires the `webhooks:manage` or `org:admin` scope.

- **Scopes:** `org:admin` or `webhooks:manage`
- **Returns:** `WebhookSubscription`
- Never retried: it is not safe to replay.
- Requires `if_match` (an ETag or the object read); a stale one raises `PreconditionFailedError`.
- A merge patch: omitted arguments stay unchanged; `None` clears a field.

## Event types

Events from `events.list`, `events.tail` and `Webhook.construct_event` are a union of these models; an Event type this version doesn't know arrives as `UnknownEvent`.

| Event type | Model | `data` |
| --- | --- | --- |
| `certificate.revoked` | `EventCertificateRevoked` | `CertificateRevokedEventData` |
| `enrollment.certified` | `EventEnrollmentCertified` | `EnrollmentCertifiedEventData` |
| `invite.bounced` | `EventInviteBounced` | `LearnerEventData` |
| `learner.certified` | `EventLearnerCertified` | `LearnerEventData` |
| `learner.expired` | `EventLearnerExpired` | `LearnerEventData` |
| `learner.expiring` | `EventLearnerExpiring` | `LearnerEventData` |
| `learner.invited` | `EventLearnerInvited` | `LearnerEventData` |
| `learner.removed` | `EventLearnerRemoved` | `LearnerEventData` |
| `learner.started` | `EventLearnerStarted` | `LearnerEventData` |
| `seat.consumed` | `EventSeatConsumed` | `dict[str, Any]` |
| `seat.freed` | `EventSeatFreed` | `dict[str, Any]` |
| `seats.low` | `EventSeatsLow` | `SeatsLowEventData` |
