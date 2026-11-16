"""Sync a roster CSV into TeachMeHIPAA, keyed by your own employee ids.

    TMH_CLIENT_ID=cli_... TMH_CLIENT_SECRET=tmh_cs_... \\
        python examples/sync_roster.py roster.csv hipaa-2026

The CSV needs `employee_id`, `email` and `name` columns. Each row becomes
an upsert by External ID, which creates and invites the Learner the first
time and returns them unchanged after, so the sync can run as often as you
like. A row that fails is reported and the sync goes on.
"""

import csv
import os
import sys
from pathlib import Path

from teachmehipaa import TeachMeHipaa, TeachMeHipaaError


def sync(client: TeachMeHipaa, roster: Path, course_id: str) -> int:
    """Upserts every row and returns how many failed."""
    created = existing = failed = 0
    with roster.open(newline="") as file:
        for row in csv.DictReader(file):
            try:
                result = client.learners.upsert_by_external_id(
                    row["employee_id"],
                    email=row["email"],
                    name=row["name"],
                    course_id=course_id,
                )
            except TeachMeHipaaError as error:
                failed += 1
                print(f"{row['employee_id']}: {error.code} {error}", file=sys.stderr)
                continue
            if result.created:
                created += 1
            else:
                existing += 1
    print(f"{created} invited, {existing} already enrolled, {failed} failed")
    return failed


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} ROSTER_CSV COURSE_ID", file=sys.stderr)
        return 2
    with TeachMeHipaa(
        client_id=os.environ["TMH_CLIENT_ID"],
        client_secret=os.environ["TMH_CLIENT_SECRET"],
        environment="sandbox",
        scopes=["learners:write"],
    ) as client:
        failed = sync(client, Path(sys.argv[1]), sys.argv[2])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
