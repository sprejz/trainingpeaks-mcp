#!/usr/bin/env python3
import sys
print(f"Python {sys.version}", flush=True)
print("Importing aiohttp...", flush=True)
import aiohttp
print(f"aiohttp {aiohttp.__version__}", flush=True)
from aiohttp import web
import asyncio, json, os, subprocess, uuid

PORT = int(os.environ.get("PORT", 8080))
CMD  = ["tp-mcp", "serve"]
print(f"Starting on port {PORT}, CMD={CMD}", flush=True)

async def handle_sse(request):
    session_id = str(uuid.uuid4())
    proc = await asyncio.create_subprocess_exec(
        *CMD,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    resp = web.StreamResponse(headers={
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*",
    })
    await resp.prepare(request)
    await resp.write(f"event: endpoint\ndata: /message?sessionId={session_id}\n\n".encode())
    request.app["sessions"][session_id] = {"proc": proc, "response": resp}

    async def read_stdout():
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
                await resp.write(f"data: {json.dumps(msg)}\n\n".encode())
            except:
                pass

    try:
        await asyncio.wait_for(read_stdout(), timeout=300)
    except:
        pass
    finally:
        proc.kill()
        request.app["sessions"].pop(session_id, None)
    return resp

async def handle_message(request):
    session_id = request.rel_url.query.get("sessionId")
    session = request.app["sessions"].get(session_id)
    if not session:
        return web.Response(status=404, text="Session not found")
    body = await request.read()
    session["proc"].stdin.write(body + b"\n")
    await session["proc"].stdin.drain()
    return web.Response(status=202, text="Accepted")

async def handle_health(request):
    return web.Response(text="ok")

async def handle_options(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    })

app = web.Application()
app["sessions"] = {}
app.router.add_get("/sse", handle_sse)
app.router.add_post("/message", handle_message)
app.router.add_get("/health", handle_health)
app.router.add_route("OPTIONS", "/{tail:.*}", handle_options)

print("Starting web server...", flush=True)
web.run_app(app, port=PORT, print=lambda x: print(x, flush=True))
