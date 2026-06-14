import json, pathlib
out = pathlib.Path(r"C:\Users\advay\AppData\Local\Temp\claude\C--Users-advay\b2914e17-9267-4662-a9c0-0321b446e46a\tasks\wic30gcox.output")
data = json.loads(out.read_text(encoding="utf-8"))
result = data["result"]
if isinstance(result, str):
    result = json.loads(result)
doc = result["doc"]["branchDoc"]
data = result
dest = pathlib.Path(r"C:\Users\advay\Obsidian\CADCopilot\src\cad_mcp\knowledge\inventor-context.md")
dest.write_text(doc, encoding="utf-8")
print("wrote", dest, len(doc), "chars; conventions:",
      len(data["doc"].get("conventions", [])), "recipes:", len(data["doc"].get("featureRecipes", [])))
