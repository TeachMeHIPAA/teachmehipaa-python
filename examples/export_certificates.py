"""Export the Organization's Certificates to a CSV file.

    TMH_CLIENT_ID=cli_... TMH_CLIENT_SECRET=tmh_cs_... \\
        python examples/export_certificates.py certificates.csv
"""

import os
import sys
from pathlib import Path

from teachmehipaa import OperationFailedError, OperationTimeoutError, TeachMeHipaa


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "certificates.csv")
    with TeachMeHipaa(
        client_id=os.environ["TMH_CLIENT_ID"],
        client_secret=os.environ["TMH_CLIENT_SECRET"],
        environment="sandbox",
        scopes=["certificates:read"],
    ) as client:
        operation = client.certificates.export(format="csv")
        try:
            export = operation.wait(timeout=120).export_result()
        except (OperationFailedError, OperationTimeoutError) as error:
            print(f"The export didn't finish: {error}", file=sys.stderr)
            return 1
    # The CSV has CRLF line endings; newline="" writes them as they are.
    target.write_text(export.csv, newline="")
    print(f"Wrote {export.row_count} Certificates to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
