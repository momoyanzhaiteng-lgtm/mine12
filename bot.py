import os
import asyncio
import threading
from flask import Flask
import discord
from huggingface_hub import InferenceClient

# --------------------------------------------------
# Webサーバー設定（Renderのスリープ防止・ヘルスチェック用）
# --------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))

# Flaskを別スレッドでバックグラウンド起動
threading.Thread(target=run_flask).start()

# --------------------------------------------------
# 環境変数と設定
# --------------------------------------------------
TOKEN = os.getenv("TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# 指定チャンネルIDの取得（タイポ修正済み）
env_channels = os.getenv("ALLOWED_CHANNEL_ID", "")
ALLOWED_CHANNEL_IDS = [int(ch_id.strip()) for ch_id in env_channels.split(",") if ch_id.strip().isdigit()]

# Hugging Face AIクライアント
hf_client = InferenceClient(
    model="Qwen/Qwen2.5-Coder-32B-Instruct",
    token=HF_TOKEN
)

# 固定回答パターン
FIXED_RESPONSES = {
    "ルール教えて": "このサーバーのルールは：みんな仲良く、迷惑行為禁止です。",
    "おはよう": "おはようございます！今日も良い一日を。",
    "助けて": "どうしましたか？できる範囲でサポートします。",
    "ping": "pong!",
}

# qa.txt から知識データを読み込む関数
def load_knowledge_base() -> str:
    file_path = "qa.txt"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"qa.txt読み込みエラー: {e}")
            return ""
    return ""

# AI回答生成処理
async def ask_ai(prompt: str) -> str:
    knowledge = load_knowledge_base()
    system_instruction = (
        "あなたはゲームの親切な公式アシスタントです。\n"
        "【公式知識ベース】の内容を参照し、ユーザーの質問に丁寧で自然な日本語で答えてください。\n"
        "Bot自身ができることの紹介や基本的な挨拶には親切に対応してください。\n"
        "探索イベント（「〇〇を探せ」など）の質問については、イベント名が違っていてもキーワード（ヒント）が一致していれば知識ベースを参照して答えてください。\n"
        "記載がない場合は「申し訳ありません、その件に関するデータがありません」と答えてください。\n\n"
        f"【公式知識ベース】\n{knowledge}"
    )

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]

    loop = asyncio.get_running_loop()
    for attempt in range(2):
        try:
            response = await loop.run_in_executor(
                None,
                lambda: hf_client.chat_completion(
                    messages=messages,
                    max_tokens=300,
                    temperature=0.6
                )
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(1)
            else:
                return "現在AIサーバーが混み合っているか、通信エラーが発生しました。時間を置いて再度お試しください。"

# --------------------------------------------------
# Discord Bot 本体処理
# --------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"ログイン成功: {client.user}")

@client.event
async def on_message(message: discord.Message):
    # Bot自身の発言は無視
    if message.author == client.user:
        return

    # 指定されたチャンネル以外は無視
    if ALLOWED_CHANNEL_IDS and message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    user_input = message.content.strip()
    if not user_input:
        return

    # 固定回答の判定
    for key, fixed_reply in FIXED_RESPONSES.items():
        if key in user_input:
            await message.reply(fixed_reply)
            return

    # AI応答（名前呼び・メンションなしで全応答）
    reply_msg = await message.reply("考え中… 🤔")
    ai_response = await ask_ai(user_input)
    await reply_msg.edit(content=ai_response)

client.run(TOKEN)