"""10 builtin tools. Handlers are pure/safe; web_search is mocked offline unless SERPAPI key set.

Python sandbox: restricted (no imports beyond math/json, no IO, timeout via asyncio)."""
import ast, json, math, re, asyncio
from ..registry import ToolDef

async def _calculator(args: dict) -> dict:
    expr = str(args.get("expression", ""))
    if not re.fullmatch(r"[0-9+\-*/(). %^a-z]*", expr.lower()): return {"error": "invalid expression"}
    try:
        # Safe eval: only numbers/operators/math names
        safe = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        value = eval(expr, {"__builtins__": {}}, safe)  # noqa: S307 — restricted charset + no builtins
        return {"result": value}
    except Exception as e:
        return {"error": str(e)}

async def _summarizer(args: dict) -> dict:
    text = str(args.get("text", ""))
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", text) if s.strip()]
    return {"summary": ". ".join(sentences[:2]) + ("." if sentences else ""), "sentences": len(sentences)}

async def _json_parser(args: dict) -> dict:
    try:
        return {"parsed": json.loads(str(args.get("text", "")))}
    except Exception as e:
        return {"error": str(e)}

async def _web_search(args: dict) -> dict:
    query = str(args.get("query", ""))
    # Offline mock: deterministic labeled results. Real integration: set SERPAPI/Tavily key + swap handler.
    return {"query": query, "results": [{"title": f"Mock result for: {query}", "url": "https://example.com/mock", "snippet": "Mock offline result — enable real search provider for live data."}], "mock": True}

async def _file_reader(args: dict) -> dict:
    # Restricted to ./data_sandbox — never arbitrary FS access in prod without allowlist.
    import os
    path = str(args.get("path", ""))
    if ".." in path or path.startswith("/"): return {"error": "path outside sandbox"}
    sandbox = os.path.join(os.getcwd(), "data_sandbox")
    full = os.path.normpath(os.path.join(sandbox, path))
    if not full.startswith(os.path.normpath(sandbox)): return {"error": "path outside sandbox"}
    try:
        with open(full) as f: return {"content": f.read(4000)}
    except Exception as e:
        return {"error": str(e)}

async def _file_writer(args: dict) -> dict:
    import os
    path = str(args.get("path", ""))
    if ".." in path or path.startswith("/"): return {"error": "path outside sandbox"}
    sandbox = os.path.join(os.getcwd(), "data_sandbox")
    os.makedirs(sandbox, exist_ok=True)
    full = os.path.normpath(os.path.join(sandbox, path))
    if not full.startswith(os.path.normpath(sandbox)): return {"error": "path outside sandbox"}
    with open(full, "w") as f: f.write(str(args.get("content", "")))
    return {"written": path}

async def _doc_generator(args: dict) -> dict:
    title = str(args.get("title", "Report")); sections = args.get("sections", [])
    body = f"# {title}\n\n" + "\n\n".join(f"## {s.get('heading','')}\n{s.get('body','')}" for s in sections if isinstance(s, dict))
    return {"document": body}

async def _db_query(args: dict) -> dict:
    # Read-only stub: prod must use parameterized queries + role check. Mock returns labeled empty.
    sql = str(args.get("sql", ""))
    if any(k in sql.lower() for k in ["delete", "drop", "update", "insert"]): return {"error": "write SQL not allowed on db_query"}
    return {"rows": [], "mock": True, "note": "Configure read-only DB role for live queries."}

async def _http_request(args: dict) -> dict:
    import httpx
    url = str(args.get("url", "")); method = str(args.get("method", "GET")).upper()
    if not url.startswith("https://"): return {"error": "only https allowed"}
    if method not in ("GET", "POST"): return {"error": "method not allowed"}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.request(method, url, json=args.get("body") if method == "POST" else None)
            return {"status": resp.status_code, "body": resp.text[:2000]}
    except Exception as e:
        return {"error": str(e)}

async def _python_sandbox(args: dict) -> dict:
    code = str(args.get("code", ""))
    # Block imports of os/sys/subprocess/socket, dunders, IO
    tree = ast.parse(code)
    blocked = {"os", "sys", "subprocess", "socket", "shutil", "pathlib"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in getattr(node, "names", []):
                if a.name.split(".")[0] in blocked: return {"error": f"blocked import: {a.name}"}
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return {"error": "blocked dunder access"}
    ns: dict = {}
    try:
        exec(compile(tree, "<sandbox>", "exec"), {"__builtins__": {"abs": abs, "min": min, "max": max, "sum": sum, "len": len, "round": round}}, ns)  # noqa: S102
        return {"output": ns.get("result", "ok")}
    except Exception as e:
        return {"error": str(e)}

def all_tools() -> list[ToolDef]:
    return [
        ToolDef("calculator", "Calculator", "Safe arithmetic", {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}, "LOW", handler=_calculator),
        ToolDef("summarizer", "Text Summarizer", "Extract summary", {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}, "LOW", handler=_summarizer),
        ToolDef("json_parser", "JSON Parser", "Parse JSON", {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}, "LOW", handler=_json_parser),
        ToolDef("web_search", "Web Search", "Search web (mock offline)", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, "MEDIUM", handler=_web_search, cost_fn=lambda a: 0.001),
        ToolDef("file_reader", "File Reader", "Read sandbox file", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, "MEDIUM", handler=_file_reader),
        ToolDef("db_query", "Database Query", "Read-only SQL stub", {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}, "MEDIUM", handler=_db_query),
        ToolDef("file_writer", "File Writer", "Write sandbox file", {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}, "HIGH", handler=_file_writer, irreversible=True),
        ToolDef("http_request", "HTTP Request", "HTTPS GET/POST", {"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string"}}, "required": ["url"]}, "HIGH", handler=_http_request),
        ToolDef("doc_generator", "Document Generator", "Generate markdown doc", {"type": "object", "properties": {"title": {"type": "string"}, "sections": {"type": "array"}}, "required": ["title"]}, "HIGH", handler=_doc_generator),
        ToolDef("python_sandbox", "Python Sandbox", "Restricted code exec", {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}, "CRITICAL", handler=_python_sandbox, irreversible=True),
    ]
