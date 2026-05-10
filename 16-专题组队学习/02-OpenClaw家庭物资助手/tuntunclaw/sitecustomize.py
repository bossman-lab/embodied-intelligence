import site
import sys


def _drop_user_site_packages() -> None:
    paths_to_remove = set()

    user_site = None
    try:
        user_site = site.getusersitepackages()
    except Exception:
        user_site = None

    if user_site:
        paths_to_remove.add(user_site)

    for path in list(sys.path):
        if "AppData\\Roaming\\Python\\Python311\\site-packages" in path:
            paths_to_remove.add(path)

    if not paths_to_remove:
        return

    sys.path[:] = [p for p in sys.path if p not in paths_to_remove]


_drop_user_site_packages()
