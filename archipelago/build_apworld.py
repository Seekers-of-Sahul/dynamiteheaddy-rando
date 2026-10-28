#!/usr/bin/env python3
"""Build headdy.apworld from this folder.

The world uses the randomizer and the hub patch from ../randomizer, so they are
copied in here rather than kept twice in the repo.

  python build_apworld.py            writes headdy.apworld next to this script
"""
import json
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.join(HERE, "headdy")
SHARED = [os.path.join(HERE, "..", "randomizer", f) for f in ("headdy_rando.py", "ap_hub_patch.py")]
OUT = os.path.join(HERE, "headdy.apworld")

# Fields Archipelago's own builder adds to the manifest (apworld format version).
MANIFEST_EXTRA = {"compatible_version": 7, "version": 7}


def main():
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(WORLD):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in sorted(files):
                if f.endswith(".pyc") or f in ("headdy_rando.py", "ap_hub_patch.py"):
                    continue
                path = os.path.join(root, f)
                arc = os.path.join("headdy", os.path.relpath(path, WORLD)).replace(os.sep, "/")
                if f == "archipelago.json":
                    with open(path) as fh:
                        manifest = json.load(fh)
                    manifest.update(MANIFEST_EXTRA)
                    z.writestr(arc, json.dumps(manifest))
                else:
                    z.write(path, arc)
        for path in SHARED:
            z.write(path, "headdy/" + os.path.basename(path))
    with open(os.path.join(WORLD, "archipelago.json")) as fh:
        version = json.load(fh)["world_version"]
    print("wrote %s (world version %s)" % (OUT, version))


if __name__ == "__main__":
    main()
