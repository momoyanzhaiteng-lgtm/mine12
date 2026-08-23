import discord
import requests
import json
import os

# Discord bot token
TOKEN = os.getenv("TOKEN")

# HuggingFace API
HF_API_URL = "https://api-inference.huggingface.co/models/google/gemma-2-2b-it"
HF_TOKEN = os.getenv("HF_TOKEN")   # ← 追加
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {HF_TOKEN}"   # ← 変更
}

# 固定回答
FIXED_RESPONSES = {
    "ルール教えて": "このサーバーのルールは：みんな仲良く、迷惑行為禁止です。",
    "おはよう": "おはようございます！今日も良い一日を。",
    "助けて": "どうしましたか？できる範囲でサポートします。",
    "ping": "pong!",
}

# AIに質問
def ask_ai(prompt):
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.7
        }
    }
    response = requests.post(HF_API_URL, headers=HEADERS, data=json.dumps(payload))
    try:
        data = response.json()
        return data[0]["generated_text"]
    except:
        return "AIの応答を取得できませんでした。もう一度試してください。"

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user in message.mentions:
        user_input = message.content.replace(f"<@{client.user.id}>", "").strip()

        for key, fixed_reply in FIXED_RESPONSES.items():
            if key in user_input:
                await message.reply(fixed_reply)
                return

        await message.reply("考え中…")
        ai_response = ask_ai(user_input)
        await message.reply(ai_response)

client.run(TOKEN)
