import os
import asyncio
import discord
from huggingface_hub import InferenceClient

TOKEN = os.getenv("TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# 無料API対応モデル（32Bは知識参照と日本語生成の精度が高くおすすめです）
hf_client = InferenceClient(
    model="Qwen/Qwen2.5-Coder-32B-Instruct",
    token=HF_TOKEN
)

# 固定回答（挨拶や一発応答用）
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
            print(f"qa.txtの読み込みエラー: {e}")
            return ""
    else:
        print("警告: qa.txt が見つかりません。")
        return ""

# AIに非同期で質問を送る関数（リトライ機能付き）
async def ask_ai(prompt: str) -> str:
    knowledge = load_knowledge_base()

    system_instruction = (
        "あなたは親切で優秀なゲームアシスタントです。\n"
        "以下の【公式知識ベース】の内容を参照し、日本語で簡潔に、必要な情報だけを返答してください。\n"
        "もし知識ベースに回答の根拠となる記載がない場合は、無理に推測せず「申し訳ありません、その件に関するデータがありません」とだけ返答してください。\n\n"
        f"【公式知識ベース】\n{knowledge}"
    )

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]

    loop = asyncio.get_running_loop()

    # 最大2回試行するリトライループ
    for attempt in range(2):
        try:
            response = await loop.run_in_executor(
                None,
                lambda: hf_client.chat_completion(
                    messages=messages,
                    max_tokens=300,
                    temperature=0.3
                )
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            if attempt == 0:
                print(f"1回目のAPI呼び出しに失敗（再試行します）: {e}")
                await asyncio.sleep(1)  # 1秒待機してリトライ
            else:
                print(f"2回目のAPI呼び出しも失敗: {e}")
                return "現在AIサーバーが混み合っているか、通信エラーが発生しました。時間を置いて再度お試しください。"

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

    # Botへのメンションを検知
    if client.user in message.mentions:
        # メンション部分を除去してユーザーの質問文を取得
        user_input = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "").strip()

        if not user_input:
            await message.reply("何かご用ですか？ゲームについての質問を入力してください！")
            return

        # 固定回答の判定
        for key, fixed_reply in FIXED_RESPONSES.items():
            if key in user_input:
                await message.reply(fixed_reply)
                return

        # AIによるQ&A回答
        reply_msg = await message.reply("考え中… 🤔")
        ai_response = await ask_ai(user_input)
        await reply_msg.edit(content=ai_response)

client.run(TOKEN)