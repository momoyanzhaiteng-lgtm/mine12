import os
import asyncio
import discord
from huggingface_hub import InferenceClient

TOKEN = os.getenv("TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Hugging Face 公式クライアントの初期化
hf_client = InferenceClient(
    model="Qwen/Qwen2.5-7B-Instruct",
    token=HF_TOKEN
)

FIXED_RESPONSES = {
    "ルール教えて": "このサーバーのルールは：みんな仲良く、迷惑行為禁止です。",
    "おはよう": "おはようございます！今日も良い一日を。",
    "助けて": "どうしましたか？できる範囲でサポートします。",
    "ping": "pong!",
}

# AIへ質問する関数（公式ライブラリを非同期実行）
async def ask_ai(prompt: str) -> str:
    messages = [
        {"role": "system", "content": "あなたは親切で優秀なアシスタントです。日本語で短く分かりやすく回答してください。"},
        {"role": "user", "content": prompt}
    ]

    try:
        # 重い処理を別スレッドで実行してDiscord Botの同期を止めないようにする
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: hf_client.chat_completion(
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"通信エラーが発生しました: {str(e)}"

# --- 以下、Discord Botのon_messageなどの処理はそのまま ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if client.user in message.mentions:
        user_input = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "").strip()

        if not user_input:
            await message.reply("何かご用ですか？質問を入力してください！")
            return

        for key, fixed_reply in FIXED_RESPONSES.items():
            if key in user_input:
                await message.reply(fixed_reply)
                return

        reply_msg = await message.reply("考え中… 🤔")
        ai_response = await ask_ai(user_input)
        await reply_msg.edit(content=ai_response)

client.run(TOKEN)