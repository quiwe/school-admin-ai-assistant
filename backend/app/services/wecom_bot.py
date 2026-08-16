import asyncio
import logging

from aibot import WSClient, WSClientOptions, generate_req_id

from ..database import SessionLocal
from ..models import ReplyHistory
from ..routers.reply import generate_reply
from ..schemas import GenerateReplyRequest
from .wecom_config import WeComConfig, load_wecom_config

logger = logging.getLogger(__name__)


class WeComBotService:
    def __init__(self) -> None:
        self._client: WSClient | None = None
        self._config: WeComConfig | None = None
        self._task: asyncio.Task[None] | None = None
        self._processed_ids: list[str] = []
        self._running = False
        self._last_error: str | None = None
        # 限制并发消息处理，避免消息洪峰时线程/SQLite 连接被耗尽。
        self._semaphore = asyncio.Semaphore(4)
        self._handler_tasks: set[asyncio.Task[None]] = set()

    def is_running(self) -> bool:
        return self._running and self._client is not None and self._client.is_connected

    def get_last_error(self) -> str | None:
        return self._last_error

    def apply_saved_config(self) -> None:
        with SessionLocal() as db:
            config = load_wecom_config(db, include_secret=True)
        self._apply(config)

    def _apply(self, config: WeComConfig) -> None:
        self.stop_sync()
        self._config = config

        if not config.enabled:
            self._last_error = None
            return
        if not config.bot_id or not config.secret:
            self._last_error = "Bot ID 或 Secret 缺失，无法启动企业微信机器人。"
            logger.warning("WeCom bot is enabled but bot_id or secret is missing.")
            return

        self._last_error = None
        self._client = WSClient(
            WSClientOptions(
                bot_id=config.bot_id,
                secret=config.secret,
                max_reconnect_attempts=-1,
            )
        )
        self._setup_handlers()
        self._task = asyncio.ensure_future(self._run())

    def _setup_handlers(self) -> None:
        client = self._client
        if not client:
            return

        @client.on("authenticated")
        def on_authenticated():
            logger.info("WeCom bot authenticated.")
            self._running = True
            self._last_error = None

        @client.on("disconnected")
        def on_disconnected(reason: str):
            message = reason or "连接已断开"
            logger.warning(f"WeCom bot disconnected: {message}")
            self._running = False
            self._last_error = message

        @client.on("error")
        def on_error(error):
            message = str(error)
            logger.error(f"WeCom bot error: {message}")
            self._last_error = message

        @client.on("message.text")
        async def on_text(frame):
            self._spawn_handler(frame)

    def _spawn_handler(self, frame: dict) -> None:
        task = asyncio.ensure_future(self._handle_text_message(frame))
        self._handler_tasks.add(task)
        task.add_done_callback(self._handler_tasks.discard)

    async def _run(self) -> None:
        if not self._client:
            return
        try:
            await self._client.connect()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("WeCom bot connection failed.")
            self._last_error = "企业微信连接失败，详情请查看日志。"

    async def _handle_text_message(self, frame: dict) -> None:
        try:
            async with self._semaphore:
                await self._process_text_message(frame)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("WeCom bot message handler failed.")

    async def _process_text_message(self, frame: dict) -> None:
        body = frame.get("body", {})
        msg_id = body.get("msgid", "")
        if msg_id and not self._remember_message(msg_id):
            return

        sender = body.get("from")
        sender_id = (sender.get("userid", "") if isinstance(sender, dict) else "").strip()
        text = body.get("text")
        content = (text.get("content", "") if isinstance(text, dict) else "").strip()

        if not content or not sender_id:
            return
        if not self._can_access(sender_id):
            return

        answer = await asyncio.to_thread(self._generate_answer, content)

        if self._client and self._client.is_connected:
            stream_id = generate_req_id("stream")
            try:
                await self._client.reply_stream(frame, stream_id, answer, True)
            except Exception:
                logger.exception("Failed to send WeCom reply.")

    def _generate_answer(self, question: str) -> str:
        with SessionLocal() as db:
            result = generate_reply(GenerateReplyRequest(question=question), db)
            history = ReplyHistory(
                student_question=question,
                ai_answer=result.answer,
                final_answer=result.answer,
                category=result.category,
                confidence=result.confidence,
                need_human_review=result.need_human_review,
            )
            db.add(history)
            db.commit()
            return result.answer

    def _can_access(self, userid: str) -> bool:
        if not self._config:
            return False
        allowlist = self._config.allowlist or []
        if not allowlist:
            return True
        return userid in allowlist

    def _remember_message(self, msg_id: str) -> bool:
        if msg_id in self._processed_ids:
            return False
        self._processed_ids.append(msg_id)
        if len(self._processed_ids) > 200:
            self._processed_ids.pop(0)
        return True

    def stop_sync(self) -> None:
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            self._task = None
        # 取消尚未完成的消息处理任务，避免重启后在旧连接上继续写历史/回复。
        for task in list(self._handler_tasks):
            task.cancel()
        self._handler_tasks.clear()
        self._client = None
        self._running = False

    async def stop(self) -> None:
        self.stop_sync()


wecom_bot_service = WeComBotService()
