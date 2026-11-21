import unittest

from bot.cogs.commands import GeneralCog
from bot.config import BotConfig
from bot.database import DatabaseManager
from bot.memory import MemoryManager
from bot.services.ollama_service import OllamaService
from bot.utils.text import TextSplitter


class TestTextSplitter(unittest.TestCase):
    def setUp(self):
        self.splitter = TextSplitter(default_limit=50)

    def test_empty_string(self):
        self.assertEqual(self.splitter.split(""), [])

    def test_short_message(self):
        text = "Hello world!"
        chunks = self.splitter.split(text)
        self.assertEqual(chunks, ["Hello world!"])

    def test_split_on_newline(self):
        line1 = "A" * 30
        line2 = "B" * 30
        text = f"{line1}\n{line2}"
        chunks = self.splitter.split(text, limit=40)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], line1)
        self.assertEqual(chunks[1], line2)

    def test_split_on_space(self):
        text = "word " * 15  # 75 chars
        chunks = self.splitter.split(text, limit=40)
        self.assertTrue(len(chunks) >= 2)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 40)

    def test_hard_slice_fallback(self):
        text = "A" * 100
        chunks = self.splitter.split(text, limit=30)
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0], "A" * 30)
        self.assertEqual(chunks[1], "A" * 30)
        self.assertEqual(chunks[2], "A" * 30)
        self.assertEqual(chunks[3], "A" * 10)

    def test_split_chat_messages_basic(self):
        text = "who said that\n....\nちょっとだけ\ndon't make it a whole thing 😭"
        messages = self.splitter.split_chat_messages(text)
        self.assertEqual(
            messages,
            ["who said that", "....", "ちょっとだけ", "don't make it a whole thing 😭"],
        )

    def test_split_chat_messages_empty_and_blanks(self):
        self.assertEqual(self.splitter.split_chat_messages(""), [])
        self.assertEqual(self.splitter.split_chat_messages("   \n\n  \n"), [])
        text = "line1\n\n\nline2\n  \nline3"
        self.assertEqual(self.splitter.split_chat_messages(text), ["line1", "line2", "line3"])

    def test_split_chat_messages_strip_dialogue_quotes(self):
        text = '"who said that"\n\'...maybe a little.\'\n“ちょっとだけ”\n「べつに」\nB-chan: why would you ask that?\nAssistant: hello there'
        messages = self.splitter.split_chat_messages(text)
        self.assertEqual(
            messages,
            ["who said that", "...maybe a little.", "ちょっとだけ", "べつに", "why would you ask that?", "hello there"],
        )
        # Inner quotes should not be stripped
        self.assertEqual(
            self.splitter.split_chat_messages('She said "no way" to me'),
            ['She said "no way" to me'],
        )

    def test_split_chat_messages_preserves_code_blocks(self):
        text = "Check this out:\n```python\nprint('hello')\nprint('world')\n```\nCool right?"
        messages = self.splitter.split_chat_messages(text)
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0], "Check this out:")
        self.assertEqual(messages[1], "```python\nprint('hello')\nprint('world')\n```")
        self.assertEqual(messages[2], "Cool right?")

    def test_split_chat_messages_exceeds_limit(self):
        long_line = "A" * 80
        text = f"short line\n{long_line}"
        messages = self.splitter.split_chat_messages(text, max_chunk_limit=50)
        self.assertEqual(messages[0], "short line")
        self.assertEqual(messages[1], "A" * 50)
        self.assertEqual(messages[2], "A" * 30)


class TestDatabaseManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = DatabaseManager(":memory:")
        await self.db.initialize()

    async def asyncTearDown(self):
        await self.db.close()

    async def test_save_and_retrieve_history(self):
        await self.db.save_turn(guild_id=1, channel_id=10, user_id=1001, user_content="Hello", assistant_content="Hi")
        await self.db.save_turn(guild_id=1, channel_id=10, user_id=1001, user_content="How are you?", assistant_content="Fine")

        history = await self.db.get_recent_history(channel_id=10, limit_turns=5)
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0], {"role": "user", "content": "Hello"})
        self.assertEqual(history[1], {"role": "assistant", "content": "Hi"})
        self.assertEqual(history[2], {"role": "user", "content": "How are you?"})
        self.assertEqual(history[3], {"role": "assistant", "content": "Fine"})

    async def test_channel_segregation(self):
        await self.db.save_turn(guild_id=1, channel_id=10, user_id=1001, user_content="Ch 10", assistant_content="Reply 10")
        await self.db.save_turn(guild_id=1, channel_id=20, user_id=1002, user_content="Ch 20", assistant_content="Reply 20")

        history_10 = await self.db.get_recent_history(channel_id=10)
        history_20 = await self.db.get_recent_history(channel_id=20)
        self.assertEqual(len(history_10), 2)
        self.assertEqual(len(history_20), 2)
        self.assertEqual(history_10[0]["content"], "Ch 10")
        self.assertEqual(history_20[0]["content"], "Ch 20")

    async def test_delete_user_history(self):
        await self.db.save_turn(guild_id=1, channel_id=10, user_id=1001, user_content="User 1 Msg", assistant_content="Reply 1")
        await self.db.save_turn(guild_id=1, channel_id=10, user_id=1002, user_content="User 2 Msg", assistant_content="Reply 2")

        deleted_count = await self.db.delete_user_history(user_id=1001)
        self.assertGreater(deleted_count, 0)

        # Only user 1002 remains
        history = await self.db.get_recent_history(channel_id=10)
        contents = [m["content"] for m in history]
        self.assertNotIn("User 1 Msg", contents)
        self.assertIn("User 2 Msg", contents)

    async def test_clear_channel(self):
        await self.db.save_turn(guild_id=1, channel_id=10, user_id=1001, user_content="Test", assistant_content="Test")
        self.assertTrue(await self.db.clear_channel(channel_id=10))
        self.assertFalse(await self.db.clear_channel(channel_id=10))
        self.assertEqual(await self.db.get_recent_history(channel_id=10), [])

    async def test_clear_all(self):
        await self.db.save_turn(guild_id=1, channel_id=10, user_id=1001, user_content="Ch 10", assistant_content="Reply 10")
        await self.db.save_turn(guild_id=1, channel_id=20, user_id=1002, user_content="Ch 20", assistant_content="Reply 20")
        deleted = await self.db.clear_all()
        self.assertEqual(deleted, 4)
        self.assertEqual(await self.db.get_recent_history(channel_id=10), [])
        self.assertEqual(await self.db.get_recent_history(channel_id=20), [])


class TestMemoryManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = DatabaseManager(":memory:")
        await self.db.initialize()
        self.memory = MemoryManager(max_turns=3, db_manager=self.db)

    async def asyncTearDown(self):
        await self.db.close()

    async def test_initial_state(self):
        self.assertFalse(await self.memory.has_memory(1, 100))
        self.assertEqual(await self.memory.get_history(1, 100), [])

    async def test_add_turn(self):
        await self.memory.add_turn(1, 100, "Alice: Hello", "Baka!", user_id=1001)
        history = await self.memory.get_history(1, 100)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], {"role": "user", "content": "Alice: Hello"})
        self.assertEqual(history[1], {"role": "assistant", "content": "Baka!"})
        self.assertTrue(await self.memory.has_memory(1, 100))

    async def test_channel_segregation(self):
        await self.memory.add_turn(1, 100, "User 1", "Bot 1", user_id=1)
        await self.memory.add_turn(1, 200, "User 2", "Bot 2", user_id=2)
        await self.memory.add_turn(None, 300, "DM User", "DM Bot", user_id=3)

        self.assertEqual(len(await self.memory.get_history(1, 100)), 2)
        self.assertEqual(len(await self.memory.get_history(1, 200)), 2)
        self.assertEqual(len(await self.memory.get_history(None, 300)), 2)
        self.assertEqual((await self.memory.get_history(1, 100))[0]["content"], "User 1")
        self.assertEqual((await self.memory.get_history(1, 200))[0]["content"], "User 2")
        self.assertEqual((await self.memory.get_history(None, 300))[0]["content"], "DM User")

    async def test_history_capping(self):
        # max_turns = 3 means at most 6 messages returned
        for i in range(5):
            await self.memory.add_turn(1, 100, f"User {i}", f"Bot {i}", user_id=1001)

        history = await self.memory.get_history(1, 100)
        self.assertEqual(len(history), 6)
        # Should keep turns 2, 3, 4
        self.assertEqual(history[0]["content"], "User 2")
        self.assertEqual(history[-1]["content"], "Bot 4")

    async def test_clear_memory(self):
        await self.memory.add_turn(1, 100, "User", "Bot", user_id=1001)
        self.assertTrue(await self.memory.clear(1, 100))
        self.assertFalse(await self.memory.has_memory(1, 100))
        # Clearing already empty channel returns False
        self.assertFalse(await self.memory.clear(1, 100))

    async def test_forget_user(self):
        await self.memory.add_turn(1, 100, "Target msg", "Bot reply", user_id=555)
        await self.memory.add_turn(1, 100, "Other msg", "Bot reply", user_id=666)
        deleted = await self.memory.forget_user(555)
        self.assertGreater(deleted, 0)
        history = await self.memory.get_history(1, 100)
        self.assertNotIn("Target msg", [m["content"] for m in history])

    async def test_wipe_all(self):
        await self.memory.add_turn(1, 100, "User 1", "Bot 1", user_id=1001)
        await self.memory.add_turn(1, 200, "User 2", "Bot 2", user_id=1002)
        deleted = await self.memory.wipe_all()
        self.assertEqual(deleted, 4)
        self.assertEqual(await self.memory.get_history(1, 100), [])
        self.assertEqual(await self.memory.get_history(1, 200), [])


class TestOllamaService(unittest.IsolatedAsyncioTestCase):
    def test_clean_think_tags(self):

        raw = "<think>\nThinking process...\nShould I be mean?\n</think>\nBaka! What do you want?"
        cleaned = OllamaService.clean_think_tags(raw)
        self.assertEqual(cleaned, "Baka! What do you want?")

    def test_extract_reaction_valid(self):
        text = "[REACTION: 💢]\nHmph, why are you asking me?!"
        reaction, clean_text = OllamaService.extract_reaction(text)
        self.assertEqual(reaction, "💢")
        self.assertEqual(clean_text, "Hmph, why are you asking me?!")

    def test_extract_reaction_none(self):
        text = "[REACTION: NONE]\nI don't care."
        reaction, clean_text = OllamaService.extract_reaction(text)
        self.assertIsNone(reaction)
        self.assertEqual(clean_text, "I don't care.")

    def test_extract_reaction_missing(self):
        text = "Just a normal response without reaction tags."
        reaction, clean_text = OllamaService.extract_reaction(text)
        self.assertIsNone(reaction)
        self.assertEqual(clean_text, text)

    def test_build_messages_payload(self):
        config = BotConfig(discord_token="fake_token", system_prompt="Test System Prompt")
        service = OllamaService(config=config)
        history = [
            {"role": "user", "content": "Prev user"},
            {"role": "assistant", "content": "Prev assistant"},
        ]
        payload = service.build_messages_payload(history, "Current prompt")
        self.assertEqual(len(payload), 4)
        self.assertEqual(payload[0]["role"], "system")
        self.assertTrue(payload[0]["content"].startswith("Test System Prompt\n\nToday's date is "))
        self.assertEqual(payload[1], {"role": "user", "content": "Prev user"})
        self.assertEqual(payload[2], {"role": "assistant", "content": "Prev assistant"})
        self.assertEqual(payload[3], {"role": "user", "content": "Current prompt"})


    async def test_generate_response_options(self):
        from unittest.mock import AsyncMock
        config = BotConfig(
            discord_token="fake_token",
            num_predict=2048,
            num_ctx=8192,
        )
        mock_client = AsyncMock()
        mock_client.chat.return_value = {
            "message": {"content": "Response"}
        }
        service = OllamaService(config=config, client=mock_client)
        await service.generate_response([], "Hello")

        call_kwargs = mock_client.chat.call_args.kwargs
        self.assertEqual(call_kwargs["keep_alive"], "24h")
        self.assertEqual(call_kwargs["options"]["num_predict"], 2048)
        self.assertEqual(call_kwargs["options"]["num_ctx"], 8192)
        self.assertEqual(call_kwargs["options"]["temperature"], 0.80)
        self.assertEqual(call_kwargs["options"]["top_p"], 0.90)
        self.assertEqual(call_kwargs["options"]["min_p"], 0.07)
        self.assertEqual(call_kwargs["options"]["repeat_penalty"], 1.08)


class TestBotConfig(unittest.TestCase):
    def test_default_values(self):
        config = BotConfig(discord_token="fake_token")
        self.assertTrue(config.separate_messages)
        self.assertEqual(config.message_delay, 0.4)
        self.assertEqual(config.num_predict, 512)
        self.assertEqual(config.keep_alive, "24h")
        self.assertEqual(config.temperature, 0.80)
        self.assertEqual(config.top_p, 0.90)
        self.assertEqual(config.min_p, 0.07)
        self.assertEqual(config.repeat_penalty, 1.08)
        self.assertEqual(config.max_history_turns, 15)

    def test_from_env(self):
        import os
        from unittest.mock import patch

        env_vars = {
            "DISCORD_BOT_TOKEN": "test_token",
            "SEPARATE_MESSAGES": "false",
            "MESSAGE_DELAY": "1.5",
            "MIN_P": "0.10",
            "REPEAT_PENALTY": "1.15",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = BotConfig.from_env()
            self.assertFalse(config.separate_messages)
            self.assertEqual(config.message_delay, 1.5)
            self.assertEqual(config.min_p, 0.10)
            self.assertEqual(config.repeat_penalty, 1.15)


class TestChatCog(unittest.IsolatedAsyncioTestCase):
    async def test_handle_bot_mention_separate_messages(self):
        from unittest.mock import AsyncMock, MagicMock

        from bot.cogs.chat import ChatCog
        from bot.services.ollama_service import LLMResponse

        config = BotConfig(discord_token="fake", separate_messages=True, message_delay=0.0)
        bot_mock = MagicMock()
        bot_mock.user.display_name = "B-chan"

        ollama_mock = AsyncMock()
        ollama_mock.config = config
        ollama_mock.generate_response.return_value = LLMResponse(
            content="who said that\n...\nちょっとだけ\ndon't make it a whole thing 😭",
            reaction=None,
        )

        memory_mock = AsyncMock()
        memory_mock.get_history.return_value = []
        memory_mock.add_turn = AsyncMock()

        cog = ChatCog(
            bot=bot_mock,
            ollama_service=ollama_mock,
            memory_manager=memory_mock,
            text_splitter=TextSplitter(),
        )

        message_mock = AsyncMock()
        message_mock.clean_content = "@B-chan you didn't miss me?"
        message_mock.attachments = []
        message_mock.guild.id = 123
        message_mock.channel.id = 456
        message_mock.author.display_name = "Khoi"

        class DummyTypingCM:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        message_mock.channel.typing = MagicMock(return_value=DummyTypingCM())

        await cog._handle_bot_mention(message_mock)

        # Message 1 replied
        message_mock.reply.assert_called_once_with("who said that", mention_author=False)
        # Remaining 3 messages sent to channel
        self.assertEqual(message_mock.channel.send.call_count, 3)
        message_mock.channel.send.assert_any_call("...")
        message_mock.channel.send.assert_any_call("ちょっとだけ")
        message_mock.channel.send.assert_any_call("don't make it a whole thing 😭")

    async def test_handle_bot_mention_single_message_when_disabled(self):
        from unittest.mock import AsyncMock, MagicMock

        from bot.cogs.chat import ChatCog
        from bot.services.ollama_service import LLMResponse

        config = BotConfig(discord_token="fake", separate_messages=False, message_delay=0.0)
        bot_mock = MagicMock()
        bot_mock.user.display_name = "B-chan"

        full_content = "who said that\n...\nちょっとだけ\ndon't make it a whole thing 😭"
        ollama_mock = AsyncMock()
        ollama_mock.config = config
        ollama_mock.generate_response.return_value = LLMResponse(
            content=full_content,
            reaction=None,
        )

        memory_mock = AsyncMock()
        memory_mock.get_history.return_value = []
        memory_mock.add_turn = AsyncMock()

        cog = ChatCog(
            bot=bot_mock,
            ollama_service=ollama_mock,
            memory_manager=memory_mock,
            text_splitter=TextSplitter(),
        )

        message_mock = AsyncMock()
        message_mock.clean_content = "@B-chan you didn't miss me?"
        message_mock.attachments = []
        message_mock.guild.id = 123
        message_mock.channel.id = 456
        message_mock.author.display_name = "Khoi"

        class DummyTypingCM:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        message_mock.channel.typing = MagicMock(return_value=DummyTypingCM())

        await cog._handle_bot_mention(message_mock)

        # Only 1 reply sent as a single block
        message_mock.reply.assert_called_once_with(full_content, mention_author=False)
        message_mock.channel.send.assert_not_called()


class TestGeneralCog(unittest.IsolatedAsyncioTestCase):
    async def test_clear_memory_authorized(self):
        from unittest.mock import AsyncMock, MagicMock

        bot_mock = MagicMock()
        bot_mock.config.admin_user_id = 244489698771206146
        memory_mock = AsyncMock()
        memory_mock.clear.return_value = True
        bot_mock.memory_manager = memory_mock

        cog = GeneralCog(bot=bot_mock)
        ctx = AsyncMock()
        ctx.author.id = 244489698771206146
        ctx.channel.id = 123
        ctx.guild.id = 456

        await cog.clear_memory_action(ctx)
        memory_mock.clear.assert_awaited_once_with(456, 123)
        ctx.send.assert_awaited_once()
        self.assertIn("wiped clean", ctx.send.call_args[0][0])

    async def test_admin_commands_denied_when_no_admin_set(self):
        from unittest.mock import AsyncMock, MagicMock

        bot_mock = MagicMock()
        bot_mock.config.admin_user_id = 0
        cog = GeneralCog(bot=bot_mock)
        self.assertFalse(cog._is_authorized(0))
        self.assertFalse(cog._is_authorized(244489698771206146))

    async def test_clear_memory_unauthorized(self):
        from unittest.mock import AsyncMock, MagicMock

        bot_mock = MagicMock()
        bot_mock.config.admin_user_id = 244489698771206146
        memory_mock = AsyncMock()
        bot_mock.memory_manager = memory_mock

        cog = GeneralCog(bot=bot_mock)
        ctx = AsyncMock()
        ctx.author.id = 999999999  # Unauthorized

        await cog.clear_memory_action(ctx)
        memory_mock.clear.assert_not_called()
        ctx.send.assert_awaited_once()
        self.assertIn("Who said you could tell me what to do", ctx.send.call_args[0][0])

    async def test_forget_me_authorized(self):
        from unittest.mock import AsyncMock, MagicMock

        import discord

        bot_mock = MagicMock()
        bot_mock.config.admin_user_id = 244489698771206146
        memory_mock = AsyncMock()
        memory_mock.forget_user.return_value = 5
        bot_mock.memory_manager = memory_mock

        cog = GeneralCog(bot=bot_mock)
        ctx = AsyncMock()
        ctx.author.id = 244489698771206146

        target_user = MagicMock(spec=discord.User)
        target_user.id = 1001
        target_user.mention = "<@1001>"

        await cog.forget_me_action(ctx, user=target_user)
        memory_mock.forget_user.assert_awaited_once_with(1001)
        ctx.send.assert_awaited_once()
        self.assertIn("Successfully erased 5 messages", ctx.send.call_args[0][0])

    async def test_forget_me_unauthorized(self):
        from unittest.mock import AsyncMock, MagicMock

        import discord

        bot_mock = MagicMock()
        bot_mock.config.admin_user_id = 244489698771206146
        memory_mock = AsyncMock()
        bot_mock.memory_manager = memory_mock

        cog = GeneralCog(bot=bot_mock)
        ctx = AsyncMock()
        ctx.author.id = 999999999  # Unauthorized

        target_user = MagicMock(spec=discord.User)
        target_user.id = 1001

        await cog.forget_me_action(ctx, user=target_user)
        memory_mock.forget_user.assert_not_called()
        ctx.send.assert_awaited_once()
        self.assertIn("Who said you could tell me what to do", ctx.send.call_args[0][0])

    async def test_wipe_database_authorized(self):
        from unittest.mock import AsyncMock, MagicMock

        bot_mock = MagicMock()
        bot_mock.config.admin_user_id = 244489698771206146
        memory_mock = AsyncMock()
        memory_mock.wipe_all.return_value = 10
        bot_mock.memory_manager = memory_mock

        cog = GeneralCog(bot=bot_mock)
        ctx = AsyncMock()
        ctx.author.id = 244489698771206146

        await cog.wipe_database_action(ctx)
        memory_mock.wipe_all.assert_awaited_once()
        ctx.send.assert_awaited_once()
        self.assertIn("Complete database wipe finished", ctx.send.call_args[0][0])

    async def test_wipe_database_unauthorized(self):
        from unittest.mock import AsyncMock, MagicMock

        bot_mock = MagicMock()
        bot_mock.config.admin_user_id = 244489698771206146
        memory_mock = AsyncMock()
        bot_mock.memory_manager = memory_mock

        cog = GeneralCog(bot=bot_mock)
        ctx = AsyncMock()
        ctx.author.id = 999999999  # Unauthorized

        await cog.wipe_database_action(ctx)
        memory_mock.wipe_all.assert_not_called()
        ctx.send.assert_awaited_once()
        self.assertIn("Who said you could tell me what to do", ctx.send.call_args[0][0])


if __name__ == "__main__":
    unittest.main()


