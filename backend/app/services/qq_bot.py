import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx
import websockets

from ..database import SessionLocal
from ..models import ReplyHistory
from ..routers.reply import generate_reply
from ..schemas import GenerateReplyRequest
from .qq_config import QQConfig, load_qq_config, normalize_allowlist, normalize_openid

logger = logging.getLogger(__name__)

TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
BASE_URL = "https://api.sgroup.qq.com"
SANDBOX_URL = "https://sandbox.api.sgroup.qq.com"
INTENT_C2C_GROUP = 1 << 25
MAX_MESSAGE_BYTES = 1500


@dataclass
class QQMessage:
    openid: str
    content: str
    message_id: str | None = None


class QQBotService:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        self._token = ""
        self._token_expires_at = 0.0
        self._seq: int | None = None
        self._session_id = ""
        self._processed_ids: list[str] = []
        self._runtime_bound_openid: str | None = None

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def apply_saved_config(self) -> None:
        with SessionLocal() as db:
            config = load_qq_config(db, include_secret=True)
        await self.restart(config)

    async def restart(self, config: QQConfig) -> None:
        await self.stop()
        self._token = ""
        self._token_expires_at = 0.0
        self._runtime_bound_openid = None
        if not config.enabled:
            return
        if not config.app_id or not config.app_secret:
            logger.warning("QQ bot is enabled but app_id or app_secret is missing.")
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_forever(config), name="qq-bot")

    async def stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("QQ bot stopped with an error.")
        self._task = None
        self._stop_event = None

    async def _run_forever(self, config: QQConfig) -> None:
        while self._stop_event and not self._stop_event.is_set():
            try:
                await self._connect_once(config)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("QQ bot connection failed; retrying in 3 seconds.")
                await asyncio.sleep(3)

    @property
    def _base_url(self) -> str:
        return SANDBOX_URL if getattr(self, "_sandbox", False) else BASE_URL

    async def _ensure_token(self, config: QQConfig) -> str:
        loop_time = asyncio.get_running_loop().time()
        if self._token and loop_time < self._token_expires_at - 60:
            return self._token
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                TOKEN_URL,
                json={"appId": config.app_id, "clientSecret": config.app_secret},
            )
            response.raise_for_status()
            data = response.json()
        self._token = data["access_token"]
        self._token_expires_at = loop_time + int(data.get("expires_in", 7200))
        return self._token

    async def _gateway_url(self, config: QQConfig) -> str:
        token = await self._ensure_token(config)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                self._base_url + "/gateway",
                headers={"Authorization": f"QQBot {token}"},
            )
            response.raise_for_status()
            data = response.json()
        url = str(data["url"])
        if not url.startswith("wss://"):
            raise RuntimeError("QQ gateway returned an unexpected websocket URL.")
        return url

    async def _connect_once(self, config: QQConfig) -> None:
        self._sandbox = bool(config.sandbox)
        token = await self._ensure_token(config)
        gateway_url = await self._gateway_url(config)
        heartbeat_task: asyncio.Task[None] | None = None
        headers = {"Authorization": f"QQBot {token}", "X-Union-Appid": config.app_id}
        async with websockets.connect(gateway_url, additional_headers=headers) as websocket:
            async for raw in websocket:
                if self._stop_event and self._stop_event.is_set():
                    break
                payload = json.loads(raw)
                op = payload.get("op")
                data = payload.get("d") or {}
                if payload.get("s") is not None:
                    self._seq = int(payload["s"])
                if op == 10:
                    interval_ms = int(data.get("heartbeat_interval") or 30000)
                    heartbeat_task = asyncio.create_task(self._heartbeat(websocket, interval_ms))
                    await self._identify_or_resume(websocket, config)
                elif op == 0:
                    event_type = payload.get("t")
                    if event_type == "READY":
                        self._session_id = str(data.get("session_id") or "")
                        logger.info("QQ bot is online.")
                    elif event_type == "C2C_MESSAGE_CREATE":
                        await self._handle_safely(self._handle_private_message, config, data)
                    elif event_type == "GROUP_AT_MESSAGE_CREATE":
                        await self._handle_safely(self._handle_group_at_message, config, data)
                    elif event_type == "GROUP_ADD_ROBOT":
                        logger.info("QQ bot added to group: %s", data.get("group_openid", ""))
                    elif event_type == "GROUP_DEL_ROBOT":
                        logger.info("QQ bot removed from group: %s", data.get("group_openid", ""))
                    elif event_type in {"GROUP_MSG_REJECT", "GROUP_MSG_RECEIVE"}:
                        logger.info("QQ group message setting changed: %s", event_type)
                elif op == 7:
                    break
                elif op == 9:
                    self._session_id = ""
                    await self._identify(websocket, config)
        if heartbeat_task:
            heartbeat_task.cancel()

    async def _heartbeat(self, websocket: Any, interval_ms: int) -> None:
        interval = max(5, min(60, interval_ms / 1000))
        while True:
            await asyncio.sleep(interval)
            await websocket.send(json.dumps({"op": 1, "d": self._seq}))

    async def _identify_or_resume(self, websocket: Any, config: QQConfig) -> None:
        if self._session_id:
            await websocket.send(
                json.dumps(
                    {
                        "op": 6,
                        "d": {
                            "token": f"QQBot {self._token}",
                            "session_id": self._session_id,
                            "seq": self._seq,
                        },
                    }
                )
            )
            return
        await self._identify(websocket, config)

    async def _identify(self, websocket: Any, config: QQConfig) -> None:
        token = await self._ensure_token(config)
        await websocket.send(
            json.dumps(
                {
                    "op": 2,
                    "d": {"token": f"QQBot {token}", "intents": INTENT_C2C_GROUP, "shard": [0, 1]},
                }
            )
        )

    async def _handle_safely(self, handler: Any, config: QQConfig, data: dict[str, Any]) -> None:
        """隔离单条消息处理失败，避免异常冒泡导致整个 WebSocket 连接崩溃重连。"""
        try:
            await handler(config, data)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("QQ bot message handler failed; keeping connection alive.")

    async def _handle_private_message(self, config: QQConfig, data: dict[str, Any]) -> None:
        message_id = str(data.get("id") or "")
        if message_id and not self._remember_message(message_id):
            return
        content = str(data.get("content") or "").strip()
        author = data.get("author") or {}
        openid = str(author.get("member_openid") or author.get("user_openid") or "").strip()
        if not content or not openid or not self._can_access(config, openid):
            return
        answer = await asyncio.to_thread(self._generate_answer, content)
        await self._send_private_message(config, QQMessage(openid, answer, message_id))

    def _remember_message(self, message_id: str) -> bool:
        if message_id in self._processed_ids:
            return False
        self._processed_ids.append(message_id)
        if len(self._processed_ids) > 200:
            self._processed_ids.pop(0)
        return True

    def _can_access(
        self,
        config: QQConfig,
        openid: str,
        *,
        allow_auto_bind: bool = True,
        respect_runtime_bind: bool = True,
    ) -> bool:
        owner = normalize_openid(config.owner_openid)
        allowlist = normalize_allowlist(config.allowlist)
        if owner:
            return openid == owner or openid in allowlist
        if allowlist:
            return openid in allowlist
        if respect_runtime_bind and self._runtime_bound_openid:
            return openid == self._runtime_bound_openid
        if allow_auto_bind:
            self._runtime_bound_openid = openid
            logger.warning(
                "QQ bot 未配置 owner/allowlist，已自动绑定首个私聊用户 %s 为运行期 owner，建议尽快在设置中显式配置。",
                openid,
            )
            return True
        # 群聊等场景不再无条件放行：未配置 owner/allowlist 时默认拒绝，避免陌生人查询知识库。
        logger.warning("QQ bot 群消息被拒绝：未配置 owner/allowlist。")
        return False

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

    async def _handle_group_at_message(self, config: QQConfig, data: dict[str, Any]) -> None:
        message_id = str(data.get("id") or "")
        if message_id and not self._remember_message(message_id):
            return
        raw_content = str(data.get("content") or "").strip()
        group_openid = str(data.get("group_openid") or "").strip()
        author = data.get("author") or {}
        openid = str(author.get("member_openid") or author.get("user_openid") or "").strip()
        if not raw_content or not group_openid or not openid:
            return
        if not self._can_access(config, openid, allow_auto_bind=False, respect_runtime_bind=False):
            return
        content = _strip_at_mention(raw_content)
        if not content:
            return
        answer = await asyncio.to_thread(self._generate_answer, content)
        await self._send_group_message(config, group_openid, QQMessage(openid, answer, message_id))

    async def _send_private_message(self, config: QQConfig, message: QQMessage) -> None:
        token = await self._ensure_token(config)
        chunks = split_message(message.content)
        async with httpx.AsyncClient(timeout=30) as client:
            for seq, chunk in enumerate(chunks, start=1):
                body: dict[str, Any] = {"content": chunk, "msg_type": 0}
                if message.message_id:
                    body["msg_id"] = message.message_id
                    body["msg_seq"] = seq
                response = await client.post(
                    f"{self._base_url}/v2/users/{message.openid}/messages",
                    headers={
                        "Authorization": f"QQBot {token}",
                        "Content-Type": "application/json",
                        "X-Union-Appid": config.app_id,
                    },
                    json=body,
                )
                response.raise_for_status()

    async def _send_group_message(
        self, config: QQConfig, group_openid: str, message: QQMessage
    ) -> None:
        token = await self._ensure_token(config)
        chunks = split_message(message.content)
        async with httpx.AsyncClient(timeout=30) as client:
            for seq, chunk in enumerate(chunks, start=1):
                body: dict[str, Any] = {"content": chunk, "msg_type": 0}
                if message.message_id:
                    body["msg_id"] = message.message_id
                    body["msg_seq"] = seq
                response = await client.post(
                    f"{self._base_url}/v2/groups/{group_openid}/messages",
                    headers={
                        "Authorization": f"QQBot {token}",
                        "Content-Type": "application/json",
                        "X-Union-Appid": config.app_id,
                    },
                    json=body,
                )
                response.raise_for_status()


_AT_MENTION_RE = re.compile(r"<@!?\d+>")


def _strip_at_mention(text: str) -> str:
    return _AT_MENTION_RE.sub("", text).strip()


def split_message(text: str, max_bytes: int = MAX_MESSAGE_BYTES) -> list[str]:
    chunks: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining.encode("utf-8")) <= max_bytes:
            chunks.append(remaining)
            break
        current = ""
        current_bytes = 0
        for char in remaining:
            char_bytes = len(char.encode("utf-8"))
            if current and current_bytes + char_bytes > max_bytes:
                break
            current += char
            current_bytes += char_bytes
        if not current:
            break
        split_at = max(current.rfind("\n"), current.rfind(" "))
        if split_at > len(current) * 0.6:
            current = current[:split_at]
        chunks.append(current)
        remaining = remaining[len(current) :].strip()
    return chunks or [""]


qq_bot_service = QQBotService()
