"""
Download full Hunspell en + ru dictionaries into ./dict as
en.aff/en.dic/ru.aff/ru.dic.

Source: github.com/LibreOffice/dictionaries (the real LibreOffice/OpenOffice
dicts — ru_RU is Lebedev's large affixed dictionary, en_US is SCOWL-based).
Run once before building: python get_dicts.py
"""

import os
import urllib.request

BASE = "https://raw.githubusercontent.com/LibreOffice/dictionaries/master"
FILES = {
    "en.aff": f"{BASE}/en/en_US.aff",
    "en.dic": f"{BASE}/en/en_US.dic",
    "ru.aff": f"{BASE}/ru_RU/ru_RU.aff",
    "ru.dic": f"{BASE}/ru_RU/ru_RU.dic",
}


def main():
    os.makedirs("dict", exist_ok=True)
    for name, url in FILES.items():
        dest = os.path.join("dict", name)
        print(f"-> {dest}")
        urllib.request.urlretrieve(url, dest)
    print("done")


if __name__ == "__main__":
    main()
