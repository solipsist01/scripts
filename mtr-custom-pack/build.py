"""Build a small MTR resource pack with only the vehicles a world actually uses.

    python3 build.py --world /path/to/world --pack big.zip [--pack other.zip ...] \
                     --mtr-jar MTR-forge-....jar --out custom.zip [--name "My trains"] \
                     [--signs id,id --objects id,id]

Reads the vehicle ids from the world's MTR sidings (world/mtr/<dim>/sidings,
MessagePack), takes those vehicles' definitions from the given resource packs,
and copies exactly the files they need: models (.obj + .mtl + textures,
.bbmodel), textures, properties/definition JSONs (and whatever they point to),
and sounds (BVE sound bases and legacy sound bases: their sounds.json entries
plus their folder). References that MTR itself provides (found in the MTR jar)
are left out. Every reference is checked at the end; anything that can't be
found is listed. Nothing in the world or the source packs is changed.

Needs: pip install msgpack
"""

import argparse
import glob
import io
import json
import os
import re
import sys
import zipfile

import msgpack

RES = re.compile(r"^([a-z0-9_.-]+):([a-z0-9_./-]+)$")
REF_KEYS = {"modelResource", "textureResource", "modelPropertiesResource", "positionDefinitionsResource",
            "textureId", "texture_id", "model", "model_properties"}
STORED = (".png", ".ogg", ".jpg", ".zip")


def used_vehicles(world):
    """vehicle id -> number of cars, from every siding in every dimension."""
    used = {}
    for path in glob.glob(os.path.join(world, "mtr", "*", "*", "sidings", "*", "*")):
        raw = open(path, "rb").read()
        try:
            # The siding is the first object; runtime state may follow it.
            siding = msgpack.Unpacker(io.BytesIO(raw), raw=False, strict_map_key=False).unpack()
        except Exception as e:
            sys.exit(f"Can't read siding {path}: {e}")
        for car in siding.get("vehicleCars") or []:
            vid = car.get("vehicleId")
            if vid:
                used[vid] = used.get(vid, 0) + 1
    return used


def strings(o, key=""):
    if isinstance(o, str):
        yield key, o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from strings(v, k)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v, key)


class Source:
    """One resource pack (zip), with a case-insensitive file index."""

    def __init__(self, path):
        self.path = path
        self.zip = zipfile.ZipFile(path)
        self.names = {n.lower(): n for n in self.zip.namelist() if not n.endswith("/")}

    def read(self, name):
        return self.zip.read(self.names[name.lower()])

    def json(self, name):
        return json.loads(self.read(name).decode("utf-8-sig"))

    def has(self, name):
        return name.lower() in self.names

    def under(self, prefix):
        prefix = prefix.lower()
        return [orig for low, orig in self.names.items() if low.startswith(prefix)]


class Builder:
    def __init__(self, sources, mtr_jar):
        self.sources = sources
        self.mtr = Source(mtr_jar)
        self.files = {}            # output path -> Source it comes from
        self.sounds = {}           # namespace -> {event: entry}
        self.missing = []          # (what, reference)
        self.builtin = set()
        self._json_done = set()

    # --- resolving references ---------------------------------------------

    def ref(self, src, ns, path, why):
        """Add the file(s) a resource location points to; returns True if found."""
        base = f"assets/{ns}/{path}"
        if src.has(base):
            self.add(src, src.names[base.lower()])
            return True
        matches = src.under(base + ".")              # texture given without extension
        if matches:
            for m in matches:
                self.add(src, m)
            return True
        if self.mtr.has(base) or self.mtr.under(base + "."):
            self.builtin.add(base)
            return True
        self.missing.append((why, f"{ns}:{path}"))
        return False

    def add(self, src, name):
        if name in self.files:
            return
        self.files[name] = src
        low = name.lower()
        if low.endswith(".json") and name not in self._json_done:
            self._json_done.add(name)
            try:
                data = src.json(name)
            except ValueError:
                return
            for key, s in strings(data):
                m = RES.match(s.strip().lower())
                if m and key not in ("tags", "wikipediaArticle"):
                    self.ref(src, m.group(1), m.group(2), f"{name} ({key})")
        elif low.endswith(".obj") or low.endswith(".mtl"):
            folder = name.rsplit("/", 1)[0]
            for line in src.read(name).decode("utf-8", "replace").splitlines():
                parts = line.strip().split(None, 1)
                if len(parts) == 2 and (parts[0] == "mtllib" or parts[0].startswith("map_")):
                    target = os.path.normpath(f"{folder}/{parts[1].split()[-1]}").replace("\\", "/")
                    if src.has(target):
                        self.add(src, src.names[target.lower()])
                    else:
                        self.missing.append((name, parts[1]))

    def sound_base(self, src, base, prefix_sep, why):
        """A BVE/legacy sound base: its sounds.json events plus its sound folder."""
        found = False
        for ns_file in [n for n in src.names.values() if n.endswith("/sounds.json")]:
            ns = ns_file.split("/")[1]
            try:
                events = src.json(ns_file)
            except ValueError:
                continue
            for event, entry in events.items():
                if event == base or event.startswith(base + prefix_sep):
                    found = True
                    self.sounds.setdefault(ns, {})[event] = entry
                    for sound in entry.get("sounds", []):
                        name = sound if isinstance(sound, str) else sound.get("name", "")
                        sns, _, spath = name.partition(":") if ":" in name else (ns, "", name)
                        self.ref(src, sns, f"sounds/{spath}.ogg", f"sound {event}")
        folder = src.under(f"assets/mtr/sounds/{base}/")
        for name in folder:
            self.add(src, name)
        if found or folder:
            return
        mtr_events = {}
        try:
            mtr_events = self.mtr.json("assets/mtr/sounds.json")
        except (KeyError, ValueError):
            pass
        if any(e == base or e.startswith(base + prefix_sep) for e in mtr_events) or self.mtr.under(f"assets/mtr/sounds/{base}/"):
            self.builtin.add(f"sound base {base}")
        else:
            self.missing.append((why, f"sound base {base}"))

    def vehicle(self, src, v):
        vid = v["id"]
        for key, s in strings(v):
            m = RES.match(s.strip().lower())
            if m and key not in ("tags", "wikipediaArticle"):
                self.ref(src, m.group(1), m.group(2), f"{vid} ({key})")
        if v.get("bveSoundBaseResource"):
            self.sound_base(src, v["bveSoundBaseResource"], "_", f"{vid} (bveSoundBaseResource)")
        for key in ("legacySpeedSoundBaseResource", "legacyDoorSoundBaseResource"):
            if v.get(key):
                self.sound_base(src, v[key], "", f"{vid} ({key})")

    def entry(self, src, e, what):
        for key, s in strings(e):
            m = RES.match(s.strip().lower())
            if m and key not in ("tags", "wikipediaArticle"):
                self.ref(src, m.group(1), m.group(2), f"{what} {e.get('id')} ({key})")


def root_definitions(src):
    """The mtr_custom_resources.json files MTR loads: one per namespace, at its root."""
    return [n for n in src.names.values() if re.fullmatch(r"assets/[^/]+/mtr_custom_resources\.json", n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--world", required=True)
    ap.add_argument("--pack", action="append", required=True, help="source resource pack(s); the first that defines a vehicle wins")
    ap.add_argument("--mtr-jar", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="Custom MTR trains")
    ap.add_argument("--signs", default="", help="comma-separated sign ids to keep as well")
    ap.add_argument("--objects", default="", help="comma-separated object ids to keep as well")
    args = ap.parse_args()

    used = used_vehicles(args.world)
    print(f"World uses {len(used)} vehicles ({sum(used.values())} cars).")
    sources = [Source(p) for p in args.pack]
    builder = Builder(sources, args.mtr_jar)
    keep_signs = {s for s in args.signs.split(",") if s}
    keep_objects = {o for o in args.objects.split(",") if o}

    picked, signs, objects, taken = [], [], [], set()
    for src in sources:
        for defs_file in root_definitions(src):
            defs = src.json(defs_file)
            for v in defs.get("vehicles") or []:
                if v.get("id") in used and v["id"] not in taken:
                    taken.add(v["id"])
                    picked.append((src, v))
            signs += [(src, s) for s in defs.get("signs") or [] if s.get("id") in keep_signs]
            objects += [(src, o) for o in defs.get("objects") or [] if o.get("id") in keep_objects]
    for src, v in picked:
        builder.vehicle(src, v)
    for src, s in signs:
        builder.entry(src, s, "sign")
    for src, o in objects:
        builder.entry(src, o, "object")

    custom = {"vehicles": [v for _, v in picked], "signs": [s for _, s in signs], "rails": [],
              "objects": [o for _, o in objects], "lifts": []}
    mcmeta = {"pack": {"pack_format": 15, "supported_formats": {"min_inclusive": 15, "max_inclusive": 99},
                       "description": f"{args.name}: {len(picked)} vehicles"}}
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as out:
        out.writestr("pack.mcmeta", json.dumps(mcmeta, indent=2))
        icon = next((s for s in sources if s.has("pack.png")), None)
        if icon:
            out.writestr("pack.png", icon.read("pack.png"))
        out.writestr("assets/mtr/mtr_custom_resources.json", json.dumps(custom, indent=1))
        for ns, events in builder.sounds.items():
            out.writestr(f"assets/{ns}/sounds.json", json.dumps(events, indent=1))
        for name, src in sorted(builder.files.items()):
            if name.lower().endswith(("/sounds.json", "mtr_custom_resources.json")):
                continue
            kind = zipfile.ZIP_STORED if name.lower().endswith(STORED) else zipfile.ZIP_DEFLATED
            out.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), src.read(name), compress_type=kind)
        out.writestr("vehicles.txt", "\n".join(f"{v['id']}\t{v.get('name', '')}\t{os.path.basename(s.path)}"
                                               for s, v in picked) + "\n")

    not_found = sorted(set(used) - taken)
    size = os.path.getsize(args.out) / 1e6
    print(f"Wrote {args.out}: {len(picked)} vehicles, {len(signs)} signs, {len(objects)} objects, "
          f"{len(builder.files)} files, {size:.1f} MB.")
    print(f"References MTR provides itself: {len(builder.builtin)}.")
    print(f"Used vehicles not in these packs (built into MTR, or from other packs): {len(not_found)}.")
    if builder.missing:
        print(f"\nUnresolved references ({len(builder.missing)}):")
        for why, what in builder.missing:
            print(f"  {what}   <- {why}")
    else:
        print("Every reference resolved.")


if __name__ == "__main__":
    main()
