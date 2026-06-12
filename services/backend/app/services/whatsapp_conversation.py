"""
Anansi WhatsApp Conversation Handler — Routes incoming WhatsApp messages
to the AI engine, command processor, or voice note transcriber.

Connects WhatsApp users to Anansi's AI for free-form chat with full
[[Second Brain]] integration.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_db_session

logger = get_logger(__name__)


# ─── Constants ───────────────────────────────────────────────────────────────────

COMMAND_PREFIX = "/"

WELCOME_MESSAGE = (
    "👋 *Welcome to Anansi!*\n\n"
    "I'm your AI, connected to your Second Brain. Here's what you can do:\n\n"
    "💬 *Chat freely* — ask me anything about your day, tasks, or memories\n"
    "🎤 *Send voice notes* — I'll transcribe and process them\n"
    "⚡ *Quick commands:*\n"
    "  `/briefing` — Your morning briefing\n"
    "  `/tasks` — Today's tasks\n"
    "  `/record [details]` — Log a transaction or event\n"
    "  `/summary [topic]` — Summarize recent activity\n"
    "  `/graph` — Knowledge web snapshot\n"
    "  `/brain` — Brain stats\n"
    "  `/brain review` — Spaced repetition review\n"
    "  `/help` — This message\n"
    "  `/status` — Your account status\n\n"
    "Let's get started! 🕷️"
)


# ─── Conversation Handler ────────────────────────────────────────────────────────


async def handle_incoming_message(
    user_id: str,
    from_number: str,
    message_body: str,
) -> dict[str, Any]:
    """Route an incoming WhatsApp message to the appropriate handler.

    If the message starts with '/', it's treated as a command.
    If it indicates media, it's handled specially.
    Otherwise, it's sent to the AI for free-form chat with brain context.

    Args:
        user_id: The resolved user UUID.
        from_number: The sender's WhatsApp number.
        message_body: The message text content.

    Returns:
        Dict with processing result.
    """
    db = await anext(get_db_session())  # Get a fresh session
    try:
        # Check if this is a media placeholder
        if message_body.startswith("[Media type:") or message_body.startswith("[File"):
            await _send_whatsapp(
                user_id,
                from_number,
                "📎 I can only process text messages and voice notes right now. "
                "Try sending a voice note or typing a message!",
            )
            return {"status": "ok", "handler": "media_info"}

        # Check for commands
        if message_body.startswith(COMMAND_PREFIX):
            return await handle_command(user_id, from_number, message_body, db)

        # Check for welcome / first interaction
        result = await db.execute(
            text("SELECT COUNT(*) FROM messages m "
                 "JOIN conversations c ON m.conversation_id = c.id "
                 "WHERE c.user_id = :user_id AND c.channel = 'whatsapp'"),
            {"user_id": user_id},
        )
        msg_count = result.scalar() or 0

        if msg_count == 0:
            # First message — send welcome
            await _send_whatsapp(user_id, from_number, WELCOME_MESSAGE)
            # Also send as AI response
            await _store_conversation(user_id, from_number, "assistant", WELCOME_MESSAGE, db)
            await _store_conversation(user_id, from_number, "user", message_body, db)
            return {"status": "ok", "handler": "welcome"}

        # Store user message
        await _store_conversation(user_id, from_number, "user", message_body, db)

        # Route to AI
        ai_response = await _get_ai_response(user_id, from_number, message_body, db)

        # Send AI response
        await _send_whatsapp(user_id, from_number, ai_response)

        # Store AI response
        await _store_conversation(user_id, from_number, "assistant", ai_response, db)

        logger.info(
            "WhatsApp conversation message processed",
            user_id=user_id,
            handler="ai_chat",
        )
        return {"status": "ok", "handler": "ai_chat"}

    finally:
        await db.close()


async def handle_voice_note(
    user_id: str,
    from_number: str,
    media_id: str,
) -> dict[str, Any]:
    """Process an incoming voice note.

    Downloads the audio via WhatsApp API, transcribes it using
    Whisper (or configured STT provider), and sends the result
    to the AI for processing.

    Args:
        user_id: The user UUID.
        from_number: The sender's number.
        media_id: The WhatsApp media object ID.

    Returns:
        Dict with processing result.
    """
    from app.services.whatsapp import WhatsAppService

    db = await anext(get_db_session())
    try:
        svc = WhatsAppService(db=db)

        # Download the audio
        audio_bytes = await svc.download_media(media_id)
        if not audio_bytes:
            await _send_whatsapp(
                user_id,
                from_number,
                "😕 Sorry, I couldn't download your voice note. Please try again.",
            )
            return {"status": "error", "reason": "download_failed"}

        # Transcribe via Whisper
        transcription = await _transcribe_audio(audio_bytes)
        if not transcription:
            await _send_whatsapp(
                user_id,
                from_number,
                "😕 I couldn't understand the voice note. Could you try speaking more clearly or type it out?",
            )
            return {"status": "error", "reason": "transcription_failed"}

        # Store the transcribed message
        display_text = f"🎤 *Voice note transcribed:* \"{transcription}\""
        await _send_whatsapp(user_id, from_number, display_text)
        await _store_conversation(user_id, from_number, "user", transcription, db)

        # Get AI response to the transcribed text
        ai_response = await _get_ai_response(user_id, from_number, transcription, db)
        await _send_whatsapp(user_id, from_number, ai_response)
        await _store_conversation(user_id, from_number, "assistant", ai_response, db)

        logger.info(
            "Voice note processed",
            user_id=user_id,
            transcription_len=len(transcription),
        )

        return {"status": "ok", "handler": "voice_note", "transcription": transcription}

    finally:
        await db.close()


async def handle_command(
    user_id: str,
    from_number: str,
    full_command: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Parse and route a slash command.

    Args:
        user_id: The user UUID.
        from_number: The sender's number.
        full_command: The full message text (e.g., '/record Sold 20 yards').
        db: Database session.

    Returns:
        Dict with command result.
    """
    parts = full_command.strip().split()
    if not parts:
        return {"status": "error", "reason": "empty_command"}

    command = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    args_str = " ".join(args)

    from app.services.whatsapp_commands import COMMAND_HANDLERS

    if command in COMMAND_HANDLERS:
        handler = COMMAND_HANDLERS[command]
        logger.info("WhatsApp command executed", user_id=user_id, command=command)
        return await handler(user_id, from_number, args_str, db)
    else:
        await _send_whatsapp(
            user_id,
            from_number,
            f"❌ Unknown command `{command}`. Try `/help` to see available commands.",
        )
        return {"status": "error", "reason": "unknown_command", "command": command}


async def send_ai_response(user_id: str, to_number: str, response_text: str) -> None:
    """Send a formatted AI response to a WhatsApp user.

    Used by the notification dispatcher and proactive messaging system
    to push AI-generated content to users.

    Args:
        user_id: The target user UUID.
        to_number: The recipient's WhatsApp number.
        response_text: The AI-generated response text.
    """
    await _send_whatsapp(user_id, to_number, response_text)
    await _store_conversation(user_id, to_number, "assistant", response_text)


async def send_conversation_context(
    user_id: str,
    to_number: str,
    context: dict[str, Any],
) -> None:
    """Send contextual information about remembered info.

    When the AI references a memory or makes a connection, this sends
    a brief note about the context.

    Args:
        user_id: The target user UUID.
        to_number: The recipient's WhatsApp number.
        context: Dict with context info (title, snippet, links).
    """
    title = context.get("title", "Context")
    snippet = context.get("snippet", "")
    links = context.get("links", [])

    message_parts = [f"🧠 *{title}*"]
    if snippet:
        message_parts.append(f"\n{snippet}")
    if links:
        message_parts.append(f"\n🔗 *Connected to:* {', '.join(links)}")

    message = "\n".join(message_parts)
    await _send_whatsapp(user_id, to_number, message)


# ─── Internal Helpers ────────────────────────────────────────────────────────────


async def _send_whatsapp(user_id: str, to_number: str, message: str) -> None:
    """Send a WhatsApp message via the service layer.

    Falls back gracefully if the service is unavailable.
    """
    from app.services.whatsapp import WhatsAppService

    db = await anext(get_db_session())
    try:
        svc = WhatsAppService(db=db)
        await svc.send_message(user_id, to_number, message)
    except Exception as exc:
        logger.error("Failed to send WhatsApp message", user_id=user_id, error=str(exc))
    finally:
        await db.close()


async def _store_conversation(
    user_id: str,
    from_number: str,
    role: str,
    content: str,
    db: AsyncSession,
) -> str:
    """Store a WhatsApp message in the conversations table.

    Creates or reuses an existing WhatsApp conversation for the user.

    Args:
        user_id: The user UUID.
        from_number: The WhatsApp number.
        role: 'user' or 'assistant'.
        content: The message content.
        db: Database session.

    Returns:
        The message ID.
    """
    now = datetime.now(timezone.utc)

    # Find or create WhatsApp conversation
    result = await db.execute(
        text("""
            SELECT id FROM conversations
            WHERE user_id = :user_id AND channel = 'whatsapp'
            ORDER BY updated_at DESC
            LIMIT 1
        """),
        {"user_id": user_id},
    )
    row = result.first()

    if row:
        conv_id = row[0]
        await db.execute(
            text("UPDATE conversations SET updated_at = :now WHERE id = :id"),
            {"id": conv_id, "now": now},
        )
    else:
        conv_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO conversations (id, user_id, channel, title, created_at, updated_at)
                VALUES (:id, :user_id, 'whatsapp', 'WhatsApp Chat', :now, :now)
            """),
            {"id": conv_id, "user_id": user_id, "now": now},
        )

    msg_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES (:id, :conv_id, :role, :content, :now)
        """),
        {
            "id": msg_id,
            "conv_id": conv_id,
            "role": role,
            "content": content,
            "now": now,
        },
    )
    await db.commit()

    return msg_id


async def _get_ai_response(
    user_id: str,
    from_number: str,
    message: str,
    db: AsyncSession,
) -> str:
    """Get an AI response using the Second Brain context.

    In a full implementation, this would call the AI service with
    conversation history, relevant memories, and brain context.

    For now, returns a smart placeholder that demonstrates the
    available capabilities.
    """
    # TODO: Integrate with actual AI service (app.services.ai)
    # For now, return helpful placeholder responses
    message_lower = message.lower()

    if "hello" in message_lower or "hi " in message_lower or message_lower in ("hi", "hey", "hello"):
        return (
            "Hey there! 👋 I'm your Anansi AI. I can help you manage your day, "
            "track your business, and grow your Second Brain. Try:\n"
            "• `/briefing` — Your daily briefing\n"
            "• `/tasks` — Today's tasks\n"
            "• `/record [details]` — Log something\n"
            "• Just ask me anything!"
        )

    if "who are you" in message_lower or "what can you do" in message_lower:
        return (
            "I'm Anansi 🕷️ — your personal AI and Second Brain. I help you:\n\n"
            "🧠 *Remember everything* — I store facts, preferences, and patterns\n"
            "📊 *Track your business* — sales, inventory, clients\n"
            "📅 *Manage your day* — tasks, calendar, briefings\n"
            "🔗 *Connect the dots* — I find links between your data\n"
            "🎤 *Accept voice notes* — Just send me one!\n\n"
            "What would you like to do?"
        )

    # Default: acknowledge and suggest commands
    return (
        f"I received your message. 🤔\n\n"
        f"I'm still learning to have free-form conversations, "
        f"but I can already do a lot! Try these commands:\n\n"
        f"⚡ `/briefing` — Your day at a glance\n"
        f"📝 `/record {message[:30]}...` — Log this as a note\n"
        f"🧠 `/brain` — See your Second Brain stats\n"
        f"📋 `/help` — All available commands"
    )


async def _transcribe_audio(audio_bytes: bytes) -> str | None:
    """Transcribe audio bytes using OpenAI Whisper API.

    Args:
        audio_bytes: Raw audio file bytes (OGG OPUS from WhatsApp).

    Returns:
        Transcribed text string, or None if transcription failed.
    """
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.ai.openai_api_key)

        # Save to temporary file for Whisper API
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",  # Auto-detect would use language parameter
                )
            return transcript.text
        finally:
            import os
            os.unlink(tmp_path)

    except Exception as exc:
        logger.error("Audio transcription failed", error=str(exc))
        return None


__all__ = [
    "handle_incoming_message",
    "handle_voice_note",
    "handle_command",
    "send_ai_response",
    "send_conversation_context",
]
