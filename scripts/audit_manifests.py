#!/usr/bin/env python
from __future__ import annotations
import argparse
from psfce.dataio import load_manifest,validate_manifest,write_manifest_metadata


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--expected-M',type=int,default=20); ap.add_argument('--output',default='results/manifest_inventory.csv')
    a=ap.parse_args(); r=load_manifest(a.manifest); validate_manifest(r,require_disjoint=True,expected_M=a.expected_M); write_manifest_metadata(r,a.output); print(a.output)
if __name__=='__main__': main()
