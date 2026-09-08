import json
import os

from http.server import BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import Application

from app.bot import build_app


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length)

            data = json.loads(body)

            application = build_app()

            import asyncio

            async def process():
                await application.initialize()

                update = Update.de_json(
                    data,
                    application.bot
                )

                await application.process_update(update)

                await application.shutdown()

            asyncio.run(process())

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"ok": True}).encode()
            )

        except Exception as e:

            print("Webhook error:", repr(e))

            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    "ok": False,
                    "error": str(e)
                }).encode()
            )

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps({
                "status": "KiranaOps webhook is live"
            }).encode()
        )