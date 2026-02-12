#!/usr/bin/env python3
import json
with open("/tmp/mycreator_routes.json") as f:
    d = json.load(f)

print("ANALYTICS ROUTES:")
for r in sorted(d["analytics_routes"]):
    print(f"  {r}")

print(f"\nALL ROUTES ({len(d['all_routes'])} total):")
for r in sorted(d["all_routes"]):
    print(f"  {r}")
