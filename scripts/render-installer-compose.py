"""Convert the development Compose model into a versioned, image-only bundle."""
import json
import sys
from pathlib import Path

version, bundle_file, build_file = sys.argv[1:]
model = json.load(sys.stdin)
build_targets = {}
for name, service in model["services"].items():
    image = f"osint-services/{name}:{version}"
    if service.pop("build", None):
        build_targets[name] = {"image": image}
    service["image"] = image
    service["platform"] = "linux/amd64"
    service["pull_policy"] = "never"

Path(bundle_file).write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
Path(build_file).write_text(json.dumps({"services": build_targets}) + "\n", encoding="utf-8")
