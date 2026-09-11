"""Bootstrap the catalogue from live provider APIs.

This used to hold a literal list of ten series with hardcoded MangaDex cover
URLs.  Those URLs pinned specific cover filenames, which change whenever a
series' primary cover is replaced, so they rotted over time - and a couple of
the IDs pointed at the wrong series to begin with.

Everything is now fetched at run time.  This script is a thin wrapper so
``python seed_db.py`` keeps working; the management command is the real entry
point and takes the interesting flags::

    python manage.py sync_catalog --help
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spellscroll.settings")
django.setup()

from django.core.management import call_command  # noqa: E402  (after django.setup)


def main():
    limit = 80
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Usage: python seed_db.py [catalogue-size]")
            return 1

    call_command("sync_catalog", limit=limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
