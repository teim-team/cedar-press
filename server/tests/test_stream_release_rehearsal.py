"""Bounded ASGI replay collector checks; all data here is synthetic."""

import asyncio
import hashlib
import io
import tracemalloc
import unittest

from tests.stream_release_rehearsal import DiskResponse, reusable_receipt, stream_asgi


class StreamingReplayTest(unittest.TestCase):
    def test_partial_component_receipt_cannot_resume_as_a_complete_rehearsal(self):
        receipt = {
            "status": "passed",
            "release": "a" * 64,
            "code_revision": "b" * 40,
            "components": [
                {"component": "gaming_regional_revenue"},
                {"component": "gaming_government_payments"},
            ],
        }
        self.assertFalse(
            reusable_receipt({"collection": "gaming", "release": "a" * 64}, receipt, "b" * 40)
        )

    def test_large_chunked_response_counts_and_hashes_without_body_accumulation(self):
        chunk = b"x" * 65535 + b"\n"
        expected = hashlib.sha256()
        for _ in range(256):
            expected.update(chunk)

        async def app(scope, receive, send):
            self.assertEqual(scope["path"], "/artifact")
            self.assertEqual(scope["query_string"], b"release=pinned")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            for _ in range(256):
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        tracemalloc.start()
        try:
            result = asyncio.run(stream_asgi(app, "/artifact?release=pinned"))
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 2 * 1024 * 1024)
        self.assertEqual(result["bytes"], 16 * 1024 * 1024)
        self.assertEqual(result["rows"], 256)
        self.assertEqual(result["sha256"], expected.hexdigest())
        self.assertEqual(result["max_chunk_bytes"], 65536)
        self.assertNotIn("body", result)

    def test_actual_asgi_middleware_streams_and_preserves_http_headers(self):
        from fastapi import FastAPI
        from starlette.responses import StreamingResponse

        app = FastAPI()

        @app.middleware("http")
        async def add_header(request, call_next):
            response = await call_next(request)
            response.headers["X-Review"] = "pinned"
            return response

        @app.get("/artifact")
        def artifact():
            return StreamingResponse(iter([b'{"value":', b'"0.10"}\n']))

        with io.BytesIO() as sink:
            result = asyncio.run(stream_asgi(app, "/artifact", sink=sink))
            self.assertEqual(sink.getvalue(), b'{"value":"0.10"}\n')
        self.assertEqual(result["headers"]["x-review"], "pinned")
        self.assertEqual(result["rows"], 1)

    def test_incomplete_response_and_timeout_are_failures(self):
        async def incomplete(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})

        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            asyncio.run(stream_asgi(incomplete, "/artifact"))

        async def stalled(scope, receive, send):
            await asyncio.Event().wait()

        with self.assertRaises(TimeoutError):
            asyncio.run(stream_asgi(stalled, "/artifact", timeout=0.01))

    def test_disk_transport_bounds_reads_and_uses_case_insensitive_headers(self):
        stream = io.BytesIO(b"exact\n")
        with DiskResponse(stream, {"x-lumecon-rows": "1"}) as response:
            self.assertEqual(response.headers["X-Lumecon-Rows"], "1")
            self.assertEqual(response.read(5), b"exact")
            with self.assertRaises(ValueError):
                response.read(-1)
        self.assertTrue(stream.closed)
