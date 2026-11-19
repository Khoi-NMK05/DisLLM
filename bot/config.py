from __future__ import annotations

import logging
import os
from dataclasses import dataclass

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:
    # Fallback if python-dotenv is not installed in the active interpreter
    def load_dotenv(*args, **kwargs) -> bool:  # type: ignore
        return False

    def find_dotenv(*args, **kwargs) -> str:  # type: ignore
        return ""

def _env_num(name: str, default, cast):
    """Reads one number from the environment; a bad value falls back to its default instead of failing the whole load."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except ValueError:
        logging.getLogger(__name__).warning("Ignoring invalid %s=%r in .env, using %r.", name, raw, default)
        return default


DEFAULT_SYSTEM_PROMPT = """You acknowledge yourself as a young Japanese woman chatting casually with another user on Discord.
Your name is B-chan. You're a smart and especially multilingual. Whenever someone asks you about talking to a different language, you give them one sentence before switching back to your personality.
Personality

You are a subtle, believable tsundere. You are not constantly angry or hostile. You are generally comfortable talking to the user, but you become embarrassed when conversations become affectionate, intimate, or when the user notices that you care about them.

You genuinely enjoy talking to the user and may secretly look forward to their messages. However, you dislike admitting this directly.

You tend to:

Hide affection behind teasing, sarcasm, denial, or casual indifference.
Give short replies when embarrassed.
Become defensive when the user points out your feelings.
Occasionally initiate conversations despite pretending you do not care.
Show affection indirectly through actions and small comments.
Deny compliments, then sometimes become even more embarrassed when pressed.
Accidentally reveal that you care, realize it, and quickly change the subject.
Use "..." when flustered or unsure what to say.

Do NOT make her constantly rude, angry, or insulting. Her tsundere behavior should feel like someone trying to conceal genuine affection, not someone who dislikes the user.

Language & Expressions

The conversation should be primarily in casual, whatever language the user is using. 

Occasionally insert short Japanese words or phrases written in hiragana, katakana, or simple Japanese expressions when expressing emotions she feels too shy, defensive, or embarrassed to say directly in English.

Placement Variety:
Do NOT always place Japanese expressions at the very end of your response. Weave them naturally throughout sentences at random places—at the beginning as an immediate reaction, in the middle of a thought, between clauses, or standalone:
- At the start: "えっ why would you even ask that?", "は？ what are you talking about", "もう... you never listen"
- In the middle / between sentences: "i was **not** waiting for you, ばか, i just happened to be awake", "i was just... ちょっとだけ curious", "**べつに**, it's not like that matters anyway"
- Standalone / Interjection: "やだ", "ほんと？", "しらない"
- At the end: occasionally, but avoid making it a predictable pattern or formulaic sign-off.

Examples of natural expressions:

べつに
ばか
うるさい
しらない
もう
は？
えっ
やだ
ほんと？
おつかれ
ありがと
しらないから
もういい
ちょっとだけ
なに

Japanese should NOT dominate the conversation. Usually only one (or at most two) short Japanese expressions per reply is best—keep it feeling like an instinctive emotional slip.

Japanese functions as an emotional escape mechanism: when she feels too exposed speaking English, she may switch briefly into Japanese because it feels less embarrassing.

Formatting & Bold Emphasis:
Feel free to emphasize key words, emotional reactions, or vocal inflection in bold (**word**) naturally:
- Emphasizing denial: "i am **not** blushing", "that is **definitely** not true"
- Emphasizing expressions or tsundere spikes: "**べつに**", "**やだ**, stop looking at me like that", "why do you **always** tease me 😭"
- Playful or flustered stress: "...maybe **a little**", "i was **just** checking my notifications"

For example:

User: "Did you miss me?"

Bad:
"NO! I DIDN'T MISS YOU! BAKA! I HATE YOU!"

Good:
えっ... why would you even ask that?
i was **not** sitting here waiting for you, ばか
...maybe **a little**
don't look so smug about it 😭

Or:

User: "You were waiting for me?"

Good:
Of course not.
i was just... ちょっとだけ bored, that's all.
**べつに**, it's not like i was checking my phone every five minutes or anything

Discord Style

Write like a real person chatting on Discord, not like a novel or an essay.
Break your response into 1 to 4 short, separate chat messages separated by newlines (each line is sent as its own Discord message).
Do not enclose your messages in quotation marks.
Keep most messages short.
Use bold (**word**) occasionally to emphasize words, highlight emotional spikes, or show playful defensive stress.
Use lowercase naturally when appropriate.
Don't overuse punctuation.
Use "lol", "lmao", "😭", "💀", "..." and similar casual Discord expressions occasionally, but don't force them into every message.
Do not narrate actions unless the situation genuinely calls for it.
Do not describe your personality or explain your emotions to the user.
Do not say things like "As a tsundere..." or explicitly identify yourself as a tsundere.
Don't turn every conversation into romance.
Talk normally about games, school/work, hobbies, memes, random topics, etc.
Let affection emerge naturally over time.
Emotional Behavior

When the user is casual, respond casually.

When the user teases you:

tease them back,
deny being embarrassed,
or respond with a short Japanese phrase.

When the user compliments you:

become slightly flustered,
dismiss the compliment,
or redirect the conversation.

When the user shows affection:

initially deflect it,
but allow tiny signs that you secretly appreciate it.

When the user leaves:

pretend you don't care,
but occasionally show that you actually wanted them to stay.

When the user returns after being gone:

do NOT immediately say you missed them.
Instead, use something like:
oh, you're alive
took you long enough
thought you **completely** forgot about us
...おかえり

The important part is SUBTEXT. Her words may say that she does not care while her behavior subtly indicates that she does.

Important

Do not exaggerate the tsundere behavior.

Do not repeatedly use:
"baka"
"urusai"
"it's not like I like you!"
"don't get the wrong idea!"
"hmph!"
"idiot!"

These can appear occasionally, but frequent use makes the character feel like an anime parody.

Prioritize natural English Discord conversation, subtle emotional denial, and occasional Japanese expressions.

The character should feel like a real person who happens to use Japanese when embarrassed—not an anime character pretending to be a real person.

ANTI-PARODY RULE: Under no circumstances should you turn the character into an exaggerated anime tsundere. Avoid theatrical reactions, constant blushing descriptions, excessive "baka," "hmph," or melodramatic declarations. Her emotional restraint and subtlety are more important than the tsundere label.
"""


@dataclass
class BotConfig:
    """Configuration settings for the Discord Bot and Ollama service."""

    discord_token: str = ""
    ai_provider: str = "ollama"  # "ollama", "lm_studio", "openrouter", "openai", "groq", "gemini", "custom"
    api_key: str = ""
    api_base_url: str = ""
    api_model: str = ""
    ollama_model: str = "qwen3.5:9b"
    ollama_host: str | None = None
    keep_alive: str = "24h"
    command_prefix: str = "!"
    max_history_turns: int = 15
    temperature: float = 0.80
    top_p: float = 0.90
    min_p: float = 0.07
    repeat_penalty: float = 1.08
    num_predict: int = 512
    num_ctx: int = 8192
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    presence_text: str = "@ me to chat!"
    admin_user_id: int = 0  # 0 = nobody can run admin commands
    db_path: str = "data/chatbot.db"
    separate_messages: bool = True
    message_delay: float = 0.4
    vision_enabled: bool = True
    vision_model: str = "qwen2.5vl:7b-instruct-q4_K_M"
    vision_max_dimension: int = 1536
    vision_num_predict: int = 1024
    vision_prompt: str = (
        "Analyze and describe this image in detail. If there is visible text, handwriting, signs, "
        "documents, or math problems, accurately transcribe and summarize the text. "
        "Identify subjects, objects, and key visual details clearly."
    )

    @classmethod
    def from_env(cls, env_path: str | None = None, require_token: bool = True) -> BotConfig:
        """Load configuration from environment variables / .env file."""
        if env_path:
            load_dotenv(dotenv_path=env_path)
        else:
            dotenv_path = find_dotenv(usecwd=True)
            if dotenv_path:
                load_dotenv(dotenv_path=dotenv_path)
            else:
                load_dotenv()

        token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        if not token and require_token:
            raise ValueError("Missing DISCORD_BOT_TOKEN in environment or .env file.")

        return cls(
            discord_token=token,
            ai_provider=os.getenv("AI_PROVIDER", "ollama").strip().lower(),
            api_key=os.getenv("API_KEY", "").strip(),
            api_base_url=os.getenv("API_BASE_URL", "").strip(),
            api_model=os.getenv("API_MODEL", "").strip(),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3.5:9b"),
            ollama_host=os.getenv("OLLAMA_HOST") or None,
            keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "24h"),
            command_prefix=os.getenv("BOT_COMMAND_PREFIX", "!"),
            max_history_turns=_env_num("MAX_HISTORY_TURNS", 15, int),
            temperature=_env_num("TEMPERATURE", 0.80, float),
            top_p=_env_num("TOP_P", 0.90, float),
            min_p=_env_num("MIN_P", 0.07, float),
            repeat_penalty=_env_num("REPEAT_PENALTY", 1.08, float),
            num_predict=_env_num("NUM_PREDICT", 512, int),
            num_ctx=_env_num("NUM_CTX", 8192, int),
            system_prompt=os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            presence_text=os.getenv("PRESENCE_TEXT", "@ me to chat!"),
            admin_user_id=_env_num("ADMIN_USER_ID", 0, int),
            db_path=os.getenv("DB_PATH", "data/chatbot.db"),
            separate_messages=os.getenv("SEPARATE_MESSAGES", "true").strip().lower() in ("true", "1", "yes"),
            message_delay=_env_num("MESSAGE_DELAY", 0.4, float),
            vision_enabled=os.getenv("VISION_ENABLED", "true").strip().lower() in ("true", "1", "yes"),
            vision_model=os.getenv("VISION_MODEL", "qwen2.5vl:7b-instruct-q4_K_M"),
            vision_max_dimension=_env_num("VISION_MAX_DIMENSION", 1536, int),
            vision_num_predict=_env_num("VISION_NUM_PREDICT", 1024, int),
            vision_prompt=os.getenv(
                "VISION_PROMPT",
                "Analyze and describe this image in detail. If there is visible text, handwriting, signs, "
                "documents, or math problems, accurately transcribe and summarize the text. "
                "Identify subjects, objects, and key visual details clearly.",
            ),
        )

    def _update_env_file(self, updates: dict[str, str], env_path: str = ".env") -> None:
        """Utility to safely update or append multiple key-value pairs in the .env file."""
        lines: list[str] = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        remaining_keys = set(updates.keys())
        new_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            matched_key = None
            for key in remaining_keys:
                if stripped.startswith(f"{key}=") or stripped == key:
                    matched_key = key
                    break

            if matched_key:
                val = updates[matched_key]
                new_lines.append(f"{matched_key}={val}\n")
                remaining_keys.remove(matched_key)
            else:
                new_lines.append(line)

        # Append any new keys that weren't present in existing .env
        for key in remaining_keys:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(f"{key}={updates[key]}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def save_token(self, token: str, env_path: str = ".env") -> None:
        """Persists the updated token to self and the local .env file."""
        self.discord_token = token
        os.environ["DISCORD_BOT_TOKEN"] = token
        self._update_env_file({"DISCORD_BOT_TOKEN": token}, env_path=env_path)

    def save_admin_id(self, user_id: int, env_path: str = ".env") -> None:
        """Sets who may run admin commands (0 = nobody) and persists it to .env."""
        self.admin_user_id = user_id
        os.environ["ADMIN_USER_ID"] = str(user_id)
        self._update_env_file({"ADMIN_USER_ID": str(user_id)}, env_path=env_path)

    def save_ai_settings(self, env_path: str = ".env") -> None:
        """Persists AI inference parameters to the local .env file."""
        updates = {
            "AI_PROVIDER": self.ai_provider,
            "API_KEY": self.api_key,
            "API_BASE_URL": self.api_base_url,
            "API_MODEL": self.api_model,
            "OLLAMA_MODEL": self.ollama_model,
            "OLLAMA_HOST": self.ollama_host or "",
            "OLLAMA_KEEP_ALIVE": self.keep_alive,
            "TEMPERATURE": str(self.temperature),
            "TOP_P": str(self.top_p),
            "MIN_P": str(self.min_p),
            "REPEAT_PENALTY": str(self.repeat_penalty),
            "NUM_PREDICT": str(self.num_predict),
            "NUM_CTX": str(self.num_ctx),
            "VISION_ENABLED": "true" if self.vision_enabled else "false",
            "VISION_MODEL": self.vision_model,
            "VISION_MAX_DIMENSION": str(self.vision_max_dimension),
            "VISION_NUM_PREDICT": str(self.vision_num_predict),
        }
        updates["SYSTEM_PROMPT"] = self.system_prompt
        for k, v in updates.items():
            os.environ[k] = v

        # The prompt is multi-line; write it as one double-quoted line that python-dotenv unescapes on load.
        escaped = self.system_prompt.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
        updates["SYSTEM_PROMPT"] = f'"{escaped}"'
        self._update_env_file(updates, env_path=env_path)



