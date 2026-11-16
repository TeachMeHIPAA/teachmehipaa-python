"""Print the Organization's compliance and its first page of Learners.

Run it with Sandbox credentials:

    TMH_CLIENT_ID=cli_... TMH_CLIENT_SECRET=tmh_cs_... python examples/quickstart.py
"""

import os

from teachmehipaa import TeachMeHipaa


def main() -> None:
    with TeachMeHipaa(
        client_id=os.environ["TMH_CLIENT_ID"],
        client_secret=os.environ["TMH_CLIENT_SECRET"],
        environment="sandbox",
    ) as client:
        compliance = client.compliance.retrieve()
        print(f"{compliance.compliant_rate:.0%} of Learners are compliant")

        # `items` is one page; iterating the page itself would fetch them all.
        page = client.learners.list(limit=20)
        for learner in page.items:
            print(f"{learner.email:40} {learner.status}")
        if page.has_next_page():
            print("…and more")


if __name__ == "__main__":
    main()
