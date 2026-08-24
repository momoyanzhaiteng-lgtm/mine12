import os
import asyncio
import discord
from huggingface_hub import InferenceClient

TOKEN = os.getenv("TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# 無料API対応モデル（知識参照と日本語生成の精度が高くおすすめです）
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

    # AIへの指示（システムプロンプト）の構築
    system_instruction = (
        "あなたはゲームの親切な公式アシスタントです。\n"
        "【公式知識ベース】の内容を参照し、ユーザーの質問に丁寧で自然な日本語で答えてください。\n"
        "Bot自身ができることの紹介や基本的な挨拶には親切に対応してください。\n"
        "探索イベント（「〇〇を探せ」など）の質問については、イベント名が違っていても、キーワード（ヒント）が一致していれば知識ベースを参照して答えてください。\n"
        "ゲームの具体的なデータや仕様について、知識ベースに記載がない場合は「申し訳ありません、その件に関するデータがありません」と伝えてください。\n\n"
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
                    temperature=0.6  # 自然な対話のために少し引き上げ
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

    # Botの呼び名リスト（サーバー内での愛称などを追加できます）
    bot_names = [client.user.name, client.user.display_name, "桃太郎", "Bot"]

    # 1. @メンションされているかチェック
    is_mentioned = client.user in message.mentions

    # 2. 本文にBotの呼び名が含まれているかチェック
    is_called_by_name = any(name in message.content for name in bot_names if name)

    # メンションも名前での呼びかけもない場合は応答しない
    if not (is_mentioned or is_called_by_name):
        return

    # 入力テキストからメンション表記（<@ID>等）を除去
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