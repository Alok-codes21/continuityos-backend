"""Reject oversized request bodies before handing them to multipart parsing."""
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes=12 * 1024 * 1024):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        try:
            declared = int(headers.get(b'content-length', b'0'))
        except ValueError:
            declared = 0
        async def reject():
            await JSONResponse({'detail': 'Request body exceeds the 12 MB limit'}, status_code=413)(scope, receive, send)
        if declared > self.max_bytes:
            return await reject()
        chunks, total = [], 0
        while True:
            msg = await receive()
            if msg['type'] == 'http.disconnect':
                return
            total += len(msg.get('body', b''))
            if total > self.max_bytes:
                return await reject()
            chunks.append(msg)
            if not msg.get('more_body'):
                break
        index = 0
        async def replay():
            nonlocal index
            if index < len(chunks):
                msg = chunks[index]
                index += 1
                return msg
            return await receive()
        await self.app(scope, replay, send)
