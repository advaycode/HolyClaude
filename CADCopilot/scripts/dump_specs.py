"""Print a condensed implementation guide for one spec category, and write the
full specs to a markdown knowledge resource for the escape-hatch tail."""
import json, sys, pathlib

OUT = pathlib.Path(r"C:\Users\advay\AppData\Local\Temp\claude\C--Users-advay\b2914e17-9267-4662-a9c0-0321b446e46a\tasks\wv7ziq97p.output")
d = json.loads(OUT.read_text(encoding="utf-8"))
r = d["result"]
if isinstance(r, str):
    r = json.loads(r)
specs = r["specs"]

if len(sys.argv) > 1 and sys.argv[1] == "--md":
    # write full spec as a knowledge resource
    md = ["# Inventor + Fusion full API spec (for execute_script)\n",
          "Exact signatures for every feature, extracted from the makepy type library + Fusion docs.\n",
          "Use these in `execute_script` for anything without a dedicated tool.\n"]
    for s in specs:
        md.append(f"\n## {s['category']}\n")
        for t in s["tools"]:
            md.append(f"### {t['name']}\n- params: {t['mcp_params']}\n- Inventor: {t['inventor']}\n- Fusion: {t['fusion']}\n")
        if s.get("enums"):
            md.append(f"\n**enums:** {'; '.join(s['enums'])}\n")
    dest = pathlib.Path(r"C:\Users\advay\Obsidian\CADCopilot\src\cad_mcp\knowledge\full-api-spec.md")
    dest.write_text("".join(md), encoding="utf-8")
    print("wrote", dest, len("".join(md)), "chars")
    sys.exit()

cat = sys.argv[1] if len(sys.argv) > 1 else specs[0]["category"]
for s in specs:
    if s["category"] == cat:
        print(f"### {cat}: {len(s['tools'])} tools, enums: {s.get('enums')}")
        for t in s["tools"]:
            inv = t["inventor"].replace("\n", " ")
            print(f"\n[{t['name']}] {t['mcp_params']}\n  INV: {inv[:260]}")
