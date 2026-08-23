import discord
import requests
import json

# Discord bot token
import os
TOKEN = os.getenv("TOKEN")


# HuggingFaceの無料推論API（Qwen2-1.5B）
HF_API_URL = "https://api-inference.huggingface.co/models/google/gemma-2-2b-it"
HEADERS = {"Content-Type": "application/json"}

# 固定回答ルール（ここに好きなだけ追加できる）
FIXED_RESPONSES = {
    "ルール教えて": "このサーバーのルールは：みんな仲良く、迷惑行為禁止です。",
    "おはよう": "おはようございます！今日も良い一日を。",
    "助けて": "どうしましたか？できる範囲でサポートします。",
    "ping": "pong!",
}

# AIに質問を送る関数
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

# Discord Bot設定
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

    # Botがメンションされたときに反応
    if client.user in message.mentions:
        user_input = message.content.replace(f"<@{client.user.id}>", "").strip()

        # 固定回答チェック
        for key, fixed_reply in FIXED_RESPONSES.items():
            if key in user_input:
                await message.reply(fixed_reply)
                return

        # AI応答
        await message.reply("考え中…")
        ai_response = ask_ai(user_input)
        await message.reply(ai_response)

client.run(TOKEN)
