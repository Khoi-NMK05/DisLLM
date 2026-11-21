from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import ollama

from bot.config import BotConfig
from bot.custom_commands import CustomCommandManager
from bot.services.ollama_service import MAX_SEARCH_ROUNDS, OllamaService
from bot.services.search_service import SearchService, SearchServiceError
from bot.utils.text import format_sources

FAKE_RESULTS = [
    {"title": "Python 3.14 released", "href": "https://python.org/3.14", "body": "Python 3.14.0 is out."},
    {"title": "What's new", "href": "https://docs.python.org/whatsnew", "body": "Free-threading..."},
]


def make_config(**kwargs) -> BotConfig:
    return BotConfig(discord_token="t", search_enabled=True, **kwargs)


def tool_call_reply(query: str) -> dict:
    return {"message": {"content": "", "tool_calls": [{"function": {"name": "web_search", "arguments": {"query": query}}}]}}


class TestSearchService(unittest.IsolatedAsyncioTestCase):
    async def test_parses_results_and_caches(self):
        calls = []

        def fake(query, n):
            calls.append((query, n))
            return FAKE_RESULTS

        service = SearchService(make_config(search_max_results=2), search_fn=fake)
        results = await service.search("  latest   python ")
        self.assertEqual([r.url for r in results], ["https://python.org/3.14", "https://docs.python.org/whatsnew"])
        self.assertEqual(results[0].snippet, "Python 3.14.0 is out.")
        await service.search("LATEST python")
        self.assertEqual(calls, [("latest python", 2)])  # Second call hit the cache.

    async def test_no_results_is_empty_not_error(self):
        def fake(query, n):
            raise RuntimeError("No results found.")

        self.assertEqual(await SearchService(make_config(), search_fn=fake).search("x"), [])

    async def test_failure_raises_search_error(self):
        def fake(query, n):
            raise ConnectionError("network down")

        with self.assertRaises(SearchServiceError):
            await SearchService(make_config(), search_fn=fake).search("x")

    def test_format_results_marks_untrusted(self):
        service = SearchService(make_config(), search_fn=lambda q, n: [])
        text = service.format_results("q", [])
        self.assertIn("no results", text)


class TestSearchInGeneration(unittest.IsolatedAsyncioTestCase):
    def make_service(self, config: BotConfig, replies: list, search_fn=lambda q, n: FAKE_RESULTS):
        client = AsyncMock()
        client.chat.side_effect = replies
        search = SearchService(config, search_fn=search_fn)
        return OllamaService(config=config, client=client, search_service=search), client

    async def test_disabled_search_offers_no_tools(self):
        config = BotConfig(discord_token="t")
        service, client = self.make_service(config, [{"message": {"content": "hi"}}])
        resp = await service.generate_response([], "hello")
        self.assertEqual(resp.content, "hi")
        self.assertNotIn("tools", client.chat.call_args.kwargs)
        self.assertEqual(resp.sources, [])

    async def test_model_calls_tool_then_answers(self):
        service, client = self.make_service(
            make_config(), [tool_call_reply("python release"), {"message": {"content": "3.14 is out"}}]
        )
        resp = await service.generate_response([], "what's the newest python?")
        self.assertEqual(resp.content, "3.14 is out")
        self.assertEqual(resp.sources, ["https://python.org/3.14", "https://docs.python.org/whatsnew"])
        second_messages = client.chat.call_args_list[1].kwargs["messages"]
        self.assertEqual(second_messages[-1]["role"], "tool")
        self.assertIn("<search_results", second_messages[-1]["content"])

    async def test_model_answers_without_searching(self):
        service, client = self.make_service(make_config(), [{"message": {"content": "hey"}}])
        resp = await service.generate_response([], "hi")
        self.assertEqual(resp.content, "hey")
        self.assertEqual(client.chat.call_count, 1)
        self.assertIn("tools", client.chat.call_args.kwargs)

    async def test_search_rounds_are_capped(self):
        replies = [tool_call_reply(f"q{i}") for i in range(MAX_SEARCH_ROUNDS)] + [{"message": {"content": "done"}}]
        service, client = self.make_service(make_config(), replies)
        resp = await service.generate_response([], "hi")
        self.assertEqual(resp.content, "done")
        self.assertEqual(client.chat.call_count, MAX_SEARCH_ROUNDS + 1)
        self.assertNotIn("tools", client.chat.call_args.kwargs)  # Last call must answer.

    async def test_model_without_tool_support_falls_back(self):
        err = ollama.ResponseError("model does not support tools", 400)
        service, client = self.make_service(make_config(), [err, {"message": {"content": "plain"}}])
        resp = await service.generate_response([], "hi")
        self.assertEqual(resp.content, "plain")
        self.assertNotIn("tools", client.chat.call_args.kwargs)

    async def test_search_failure_still_answers(self):
        def broken(q, n):
            raise ConnectionError("down")

        service, client = self.make_service(
            make_config(), [tool_call_reply("x"), {"message": {"content": "couldn't check"}}], search_fn=broken
        )
        resp = await service.generate_response([], "news?")
        self.assertEqual(resp.content, "couldn't check")
        self.assertIn("failed", client.chat.call_args.kwargs["messages"][-1]["content"])

    async def test_search_query_injects_results_without_tools(self):
        service, client = self.make_service(make_config(), [{"message": {"content": "answer"}}])
        resp = await service.generate_response([], "Answer: python", search_query="python")
        kwargs = client.chat.call_args.kwargs
        self.assertNotIn("tools", kwargs)
        self.assertIn("<search_results", kwargs["messages"][-1]["content"])
        self.assertEqual(len(resp.sources), 2)

    async def test_openai_tool_loop(self):
        config = make_config(ai_provider="openai", api_key="k")
        bodies = [
            {"choices": [{"message": {"content": None, "tool_calls": [
                {"id": "c1", "type": "function",
                 "function": {"name": "web_search", "arguments": json.dumps({"query": "news"})}}
            ]}}]},
            {"choices": [{"message": {"content": "here's the news"}}]},
        ]
        sent = []

        class Resp:
            status = 200

            def __init__(self, body):
                self.body = body

            async def json(self):
                return self.body

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return None

        class Session:
            def __init__(self, **kw):
                pass

            def post(self, url, json=None, headers=None):
                sent.append(json)
                return Resp(bodies[len(sent) - 1])

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return None

        service = OllamaService(config, client=AsyncMock(), search_service=SearchService(config, lambda q, n: FAKE_RESULTS))
        with patch("aiohttp.ClientSession", side_effect=Session):
            resp = await service.generate_response([], "news?")
        self.assertEqual(resp.content, "here's the news")
        self.assertIn("tools", sent[0])
        tool_msg = sent[1]["messages"][-1]
        self.assertEqual(tool_msg["role"], "tool")
        self.assertEqual(tool_msg["tool_call_id"], "c1")


class TestSearchHelpers(unittest.TestCase):
    def test_format_sources(self):
        self.assertEqual(format_sources([]), "")
        line = format_sources(["https://a.com", "https://b.com", "https://c.com", "https://d.com"])
        self.assertEqual(line, "-# Sources: <https://a.com> <https://b.com> <https://c.com>")

    def test_config_reads_search_env(self):
        env = {"DISCORD_BOT_TOKEN": "t", "SEARCH_ENABLED": "true", "SEARCH_SHOW_SOURCES": "yes", "SEARCH_MAX_RESULTS": "3"}
        with patch.dict(os.environ, env):
            cfg = BotConfig.from_env(env_path=os.devnull)
        self.assertTrue(cfg.search_enabled)
        self.assertTrue(cfg.search_show_sources)
        self.assertEqual(cfg.search_max_results, 3)

    def test_old_command_files_load_without_web_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cmds.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump([{"name": "roast", "description": "d", "prompt_template": "{query}"}], f)
            mgr = CustomCommandManager(file_path=path)
            self.assertFalse(mgr.commands[0].web_search)


if __name__ == "__main__":
    unittest.main()
