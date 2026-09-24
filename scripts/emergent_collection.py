#!/usr/bin/env python3
"""Materialize an emergent wiki collection from a semantic artifact-type label."""
from __future__ import annotations
import argparse, os, re, sys


def collection_slug(type_label):
    value=type_label.strip().lower()
    value=re.sub(r"[^\w\s-]","",value,flags=re.UNICODE)
    value=re.sub(r"[\s_]+","-",value).strip("-")
    if not value or value in {"entities","concepts","research","synthesis","ideas"}:
        raise ValueError("artifact type must name a non-reserved collection")
    return value


def ensure_collection(root,type_label):
    root=os.path.realpath(root)
    if not os.path.isfile(os.path.join(root,".callosum")): raise ValueError("not a mind root")
    wiki=os.path.join(root,"wiki")
    if os.path.lexists(wiki) and (os.path.islink(wiki) or not os.path.isdir(wiki)):
        raise ValueError("unsafe wiki root")
    path=os.path.join(wiki,collection_slug(type_label))
    if os.path.lexists(path) and (os.path.islink(path) or not os.path.isdir(path)):
        raise ValueError("unsafe collection path")
    os.makedirs(path,exist_ok=True)
    if os.path.commonpath((os.path.realpath(path),wiki)) != wiki:
        raise ValueError("collection path escapes wiki root")
    return path


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("root"); ap.add_argument("type_label")
    a=ap.parse_args(argv)
    try: print(ensure_collection(os.path.abspath(a.root),a.type_label))
    except ValueError as exc: print(str(exc),file=sys.stderr); return 1
    return 0

if __name__=="__main__": sys.exit(main())
