import os
import discord
import aiohttp

# 環境変数の取得
TOKEN = os.getenv("TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# HuggingFace API設定
HF_API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {HF_TOKEN}"
}

# 固定回答データベース
FIXED_RESPONSES = {
    "ルール教えて": "このサーバーのルールは：みんな仲良く、迷惑行為禁止です。",
    "おはよう": "おはようございます！今日も良い一日を。",
    "助けて": "どうしましたか？できる範囲でサポートします。",
    "ping": "pong!",
}

# AIに非同期で質問を送る関数
async def ask_ai(prompt: str) -> str:
    # Qwen等の指示追従モデル向けにシステムプロンプトを付与
    formatted_prompt = f"System: あなたは親切で優秀なアシスタントです。日本語で短く分かりやすく回答してください。\nUser: {prompt}\nAssistant:"

    payload = {
        "inputs": formatted_prompt,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.7,
            "return_full_text": False  # 生成されたテキストのみを返す設定
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(HF_API_URL, headers=HEADERS, json=payload, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        text = data[0].get("generated_text", "").strip()
                        # 不要なプロンプト残滓を除去
                        return text if text else "回答を生成できませんでした。"
                return f"AIサーバーからエラーが返されました。(Status: {resp.status})"
    except Exception as e:
        return f"通信エラーが発生しました: {str(e)}"

# Discord Botの初期化
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")

@client.event
async def on_message(message: discord.Message):
    # Bot自身のメッセージは無視
    if message.author == client.user:
        return

    # Bot宛てのメンションがあるかチェック
    if client.user in message.mentions:
        # メンション部分を削って発言内容を取得
        user_input = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "").strip()

        if not user_input:
            await message.reply("何かご用ですか？質問を入力してください！")
            return

        # 固定回答の判定
        for key, fixed_reply in FIXED_RESPONSES.items():
            if key in user_input:
                await message.reply(fixed_reply)
                return

        # AI処理（「考え中…」を出してから編集して回答を入れる）
        reply_msg = await message.reply("考え中… 🤔")
        ai_response = await ask_ai(user_input)
        await reply_msg.edit(content=ai_response)

client.run(TOKEN)