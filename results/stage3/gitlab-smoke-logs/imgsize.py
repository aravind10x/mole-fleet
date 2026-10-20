"""Sum compressed layer sizes of a ghcr image via the registry API (no docker credential helper)."""
import json, sys, urllib.request
repo, tag = sys.argv[1], sys.argv[2]
tok = json.load(urllib.request.urlopen(f"https://ghcr.io/token?scope=repository:{repo}:pull"))["token"]
def get(path, accept):
    r = urllib.request.Request(f"https://ghcr.io/v2/{repo}/{path}", headers={"Authorization": f"Bearer {tok}", "Accept": accept})
    return json.load(urllib.request.urlopen(r))
m = get(f"manifests/{tag}", "application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json,application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json")
print("mediaType", m.get("mediaType"))
layers = m.get("layers", [])
print("layers", len(layers), "compressed GB", round(sum(l["size"] for l in layers)/1e9, 2))
for l in sorted(layers, key=lambda l: -l["size"])[:6]:
    print(round(l["size"]/1e9, 3), l["mediaType"])
