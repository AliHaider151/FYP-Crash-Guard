import logging
import os
import sys

from django.core.management import execute_from_command_line


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crashguard_site.settings")
    execute_from_command_line([sys.argv[0], "runserver", *sys.argv[1:]])


if __name__ == "__main__":
    main()
