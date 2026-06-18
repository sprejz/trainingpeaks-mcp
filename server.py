#!/usr/bin/env python3
import sys, os, asyncio, json, uuid
print("Starting...", flush=True)
from aiohttp import web
print("aiohttp ok", flush=True)

PORT = int(os.environ.get("PORT", 8080))
CMD  = ["tp-mcp", "serve"]

# Globaler persistenter tp-mcp Prozess
tp_proc = None
tp_lock = asyncio.Lock()
pending = {}  # session_id -> queue

async def ensure_tp():
    global tp_proc
    if tp_proc is None or tp_proc.returncode is not None:
        print("Starting tp-mcp...", flush=True)
        tp_proc = await asyncio.create_subprocess_exec(
            *CMD,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        asyncio.create_task(read_tp_stdout())
        print("tp-mcp started", flush=True)

async def read_tp_stdout():
    global tp_proc
    while tp_proc and tp_proc.stdout:
        try:
            line = await tp_proc.stdout.readline()
            if not line:
                break
            msg = json.loads(line)
            msg_id = str(msg.get("id"))
            if msg_id in pending:
                await pending[msg_id].put(msg)
        except Exception as e:
            print(f"stdout error: {e}", flush=True)
            break

async def handle_sse(request):
    session_id = str(uuid.uuid4())
    resp = web.StreamResponse(headers={
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*",
    })
    await resp.prepare(request)
    await resp.write(f"event: endpoint\ndata: /message?sessionId={session_id}\n\n".encode())
    request.app["sessions"][session_id] = resp
    # Offen halten bis Client trennt
    try:
        await asyncio.sleep(300)
    except:
        pass
    finally:
        request.app["sessions"].pop(session_id, None)
    return resp

async def handle_message(request):
    global tp_proc
    session_id = request.rel_url.query.get("sessionId")
    session_resp = request.app["sessions"].get(session_id)
    
    async with tp_lock:
        await ensure_tp()
    
    body = await request.read()
    msg = json.loads(body)
    msg_id = str(msg.get("id", ""))
    
    q = asyncio.Queue()
    pending[msg_id] = q
    
    tp_proc.stdin.write(body + b"\n")
    await tp_proc.stdin.drain()
    
    try:
        result = await asyncio.wait_for(q.get(), timeout=30)
        pending.pop(msg_id, None)
        if session_resp:
            await session_resp.write(f"data: {json.dumps(result)}\n\n".encode())
        return web.Response(status=202, text="Accepted")
    except asyncio.TimeoutError:
        pending.pop(msg_id, None)
        return web.Response(status=504, text="Timeout")

async def handle_health(request):
    return web.Response(text="ok")

async def handle_options(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    })

async def on_startup(app):
    await ensure_tp()

app = web.Application()
app["sessions"] = {}
app.on_startup.append(on_startup)
app.router.add_get("/sse", handle_sse)
app.router.add_post("/message", handle_message)
app.router.add_get("/health", handle_health)
app.router.add_route("OPTIONS", "/{tail:.*}", handle_options)

print(f"Starting on port {PORT}", flush=True)
web.run_app(app, port=PORT, print=lambda x: print(x, flush=True))
