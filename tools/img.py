#!/usr/bin/env python3
"""CLI mínimo sobre la Images API de OpenAI (gpt-image-1).

    python3 tools/img.py edit -i foto.png -p "prompt..." -o salida.png
    python3 tools/img.py generate -p "prompt..." -o salida.png

La key se lee de .env (OPENAI_API_KEY). Nunca se imprime.
"""
import argparse, base64, os, pathlib, sys
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://api.openai.com/v1/images"


def load_key():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("Falta OPENAI_API_KEY (ponla en .env)")
    return key


def save(resp, out, n):
    if resp.status_code != 200:
        sys.exit(f"HTTP {resp.status_code}: {resp.text[:600]}")
    data = resp.json()["data"]
    paths = []
    for idx, item in enumerate(data):
        p = pathlib.Path(out)
        if n > 1:
            p = p.with_name(f"{p.stem}-{idx + 1}{p.suffix}")
        p.write_bytes(base64.b64decode(item["b64_json"]))
        paths.append(str(p))
    usage = resp.json().get("usage", {})
    print("OK ->", ", ".join(paths))
    if usage:
        print("tokens:", usage)


def cmd_edit(a, key):
    files = [("image[]", (pathlib.Path(f).name, open(f, "rb"), "image/png")) for f in a.image]
    if a.mask:
        files.append(("mask", (pathlib.Path(a.mask).name, open(a.mask, "rb"), "image/png")))
    form = {
        "model": "gpt-image-1",
        "prompt": a.prompt,
        "size": a.size,
        "quality": a.quality,
        "n": str(a.n),
        "input_fidelity": a.fidelity,
    }
    r = requests.post(f"{API}/edits", headers={"Authorization": f"Bearer {key}"},
                      data=form, files=files, timeout=600)
    save(r, a.out, a.n)


def cmd_generate(a, key):
    body = {"model": "gpt-image-1", "prompt": a.prompt, "size": a.size,
            "quality": a.quality, "n": a.n}
    r = requests.post(f"{API}/generations",
                      headers={"Authorization": f"Bearer {key}",
                               "Content-Type": "application/json"},
                      json=body, timeout=600)
    save(r, a.out, a.n)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("-p", "--prompt", required=True)
        p.add_argument("-o", "--out", required=True)
        p.add_argument("-s", "--size", default="1024x1536")
        p.add_argument("-q", "--quality", default="high", choices=["low", "medium", "high"])
        p.add_argument("-n", type=int, default=1)

    e = sub.add_parser("edit"); common(e)
    e.add_argument("-i", "--image", required=True, nargs="+")
    e.add_argument("-m", "--mask")
    e.add_argument("--fidelity", default="high", choices=["low", "high"])

    g = sub.add_parser("generate"); common(g)

    a = ap.parse_args()
    key = load_key()
    (cmd_edit if a.cmd == "edit" else cmd_generate)(a, key)


if __name__ == "__main__":
    main()
