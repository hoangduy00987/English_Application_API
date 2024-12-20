from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django_redis import get_redis_connection
import json
import random
import string


class WordChainConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "chat_wordchain"
        self.user = self.scope["user"]
        self.nickname = None

        # Tham gia group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Tăng số lượng người dùng trong nhóm
        await self.increment_group_count()

        # Gửi lại các tin nhắn cũ
        old_messages = await self.get_stored_messages()
        for message in old_messages:
            await self.send(text_data=json.dumps({"message": message}))

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        # Kiểm tra nếu đây là message đầu tiên (gửi nickname)
        if "nickname" in text_data_json:
            original_nickname = text_data_json["nickname"]

            # Xử lý trùng nickname
            self.nickname = await self.generate_unique_nickname(original_nickname)

            # Thêm nickname vào danh sách người dùng online
            await self.add_user_to_online_list(self.nickname)

            # Gửi lại nickname đã chỉnh sửa cho client
            await self.send(text_data=json.dumps({"type": "nickname", "nickname": self.nickname}))

            # Gửi lại danh sách người dùng online
            await self.broadcast_online_users()
            return

        # Xử lý các message khác
        message = text_data_json.get("message")
        if message:
            await self.store_message(f"{self.nickname}: {message}")
            await self.channel_layer.group_send(
                self.group_name, {"type": "chat.message", "message": f"{self.nickname}: {message}"}
            )
    
    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
    
    @database_sync_to_async
    def store_message(self, message):
        # Lưu tin nhắn vào danh sách Redis
        redis_conn = get_redis_connection("default")
        redis_conn.rpush("wordchain_messages", message)
        # Đặt TTL cho danh sách tin nhắn
        redis_conn.expire("wordchain_messages", 3600)  # Hết hạn sau 1 giờ
    
    @database_sync_to_async
    def get_stored_messages(self):
        # Lấy danh sách tin nhắn từ Redis
        redis_conn = get_redis_connection("default")
        messages = redis_conn.lrange("wordchain_messages", 0, -1)
        return [msg.decode("utf-8") for msg in messages]
    
    @database_sync_to_async
    def clear_stored_messages(self):
        # Xóa danh sách tin nhắn trong Redis
        redis_conn = get_redis_connection("default")
        redis_conn.delete("wordchain_messages")

    @sync_to_async
    def add_user_to_online_list(self, nickname):
        # Thêm nickname vào Redis set
        redis_conn = get_redis_connection("default")
        redis_conn.sadd("online_users", nickname)

    @sync_to_async
    def remove_user_from_online_list(self, nickname):
        # Xóa nickname khỏi Redis set
        redis_conn = get_redis_connection("default")
        redis_conn.srem("online_users", nickname)

    @sync_to_async
    def get_online_users(self):
        # Lấy danh sách người dùng online từ Redis
        redis_conn = get_redis_connection("default")
        return list(redis_conn.smembers("online_users"))

    @sync_to_async
    def generate_unique_nickname(self, nickname):
        redis_conn = get_redis_connection("default")
        while redis_conn.sismember("online_users", nickname):
            suffix = "".join(random.choices(string.ascii_letters + string.digits, k=4))
            nickname = f"{nickname}_{suffix}"
        return nickname

    async def disconnect(self, close_code):
        if self.nickname:
            await self.remove_user_from_online_list(self.nickname)

        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.broadcast_online_users()

        # Giảm số lượng người dùng trong nhóm
        group_count = await self.decrement_group_count()

        # Nếu không còn ai trong nhóm, xóa tin nhắn tạm thời
        if group_count == 0:
            await self.clear_stored_messages()
            await self.reset_group_count()
    
    @sync_to_async
    def increment_group_count(self):
        redis_conn = get_redis_connection("default")
        return redis_conn.incr("group:chat_wordchain:count")

    @sync_to_async
    def decrement_group_count(self):
        redis_conn = get_redis_connection("default")
        count = redis_conn.decr("group:chat_wordchain:count")
        # Nếu giá trị giảm xuống âm, đặt lại về 0
        if count < 0:
            redis_conn.set("group:chat_wordchain:count", 0)
            count = 0
        return count
    
    @sync_to_async
    def reset_group_count(self):
        redis_conn = get_redis_connection("default")
        redis_conn.delete("group:chat_wordchain:count")

    async def broadcast_online_users(self):
        online_users = await self.get_online_users()
        online_users_serializable = [
            user.decode("utf-8") if isinstance(user, bytes) else user for user in online_users
        ]
        online_users_data = {
            "type": "online_users",
            "users": online_users_serializable,
            "count": len(online_users_serializable),
        }
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "online_users_message",
                "data": online_users_data,
            }
        )

    async def online_users_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))
