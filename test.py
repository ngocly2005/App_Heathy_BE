"""Minimal chat + food-photo analysis against a free OpenAI-compatible API.

Runs ONE provider/model per run. Examples:
    pip install openai
    $env:GROQ_API_KEY = "..."                      # key of the provider you pick
    python food_ai.py pho.jpg                      # default provider: groq
    python food_ai.py pho.jpg -p zai               # pick another provider
    python food_ai.py pho.jpg -p openrouter -m minimax/minimax-m3.1-flash:free
    python food_ai.py -p gemini                    # no image = chat mode
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import sys

from openai import OpenAI

# One client shape for every provider: only base_url, model and key differ.
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "qwen/qwen3.8-27b",  # free: 30 RPM, 1K req/day, 8K tokens/min
        "key_env": "GROQ_API_KEY",
    },
    # "gemini": {
    #     "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    #     "model": "gemini-3.5-flash-lite",  # free tier data may be used for training
    #     "key_env": "GEMINI_API_KEY",
    # },
    # "openrouter": {
    #     "base_url": "https://openrouter.ai/api/v1",
    #     "model": "google/gemma-4-31b-it:free",  # free: 50 req/day (1K after $10 credit)
    #     "key_env": "OPENROUTER_API_KEY",
    # },
    # # Not free: needs a topped-up balance, but ~$0.15/1M input tokens off-peak.
    # "deepseek": {
    #     "base_url": "https://api.deepseek.com",
    #     "model": "deepseek-flash",  # vision supported; deepseek-v4-pro is text-only
    #     "key_env": "DEEPSEEK_API_KEY",
    # },
    # # Free vision model; servers/affiliates in China. Model id is unverified.
    # "zai": {
    #     "base_url": "https://api.z.ai/api/paas/v4/",
    #     "model": "glm-4.6v-flash",
    #     "key_env": "ZAI_API_KEY",
    # },
}

client: OpenAI | None = None
MODEL = ""


def use(provider: str, model: str | None = None) -> None:
    """Pick the single provider (and optionally a model) for all following calls."""
    global client, MODEL
    cfg = PROVIDERS[provider]
    api_key = ""
    if not api_key:
        sys.exit(f"Missing API key: set {cfg['key_env']} for provider '{provider}'")
    MODEL = model or cfg["model"]
    client = OpenAI(base_url=cfg["base_url"], api_key=api_key)


SYSTEM_PROMPT = (
    "Bạn là trợ lý dinh dưỡng. Trả lời bằng tiếng Việt, ngắn gọn. "
    "Bạn không thay thế bác sĩ; với vấn đề bệnh lý hãy khuyên người dùng hỏi chuyên gia."
)

FOOD_PROMPT = (
    "Nhận diện món ăn trong ảnh và ước lượng dinh dưỡng cho phần ăn nhìn thấy. "
    "Chỉ trả về JSON đúng dạng: "
    '{"mon_an": [{"ten": str, "khau_phan_g": number, "kcal": number, '
    '"dam_g": number, "carb_g": number, "beo_g": number}], '
    '"tong_kcal": number, "do_tin_cay": "thap|trung_binh|cao", "ghi_chu": str}'
)


def chat(history: list[dict], user_text: str) -> str:
    """Send one chat turn; history is a list of {"role", "content"} kept by the caller."""
    history.append({"role": "user", "content": user_text})
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *history],
    )
    answer = resp.choices[0].message.content
    history.append({"role": "assistant", "content": answer})
    return answer


def analyze_food(image_path: str) -> dict:
    """Send a local image as a base64 data URL and parse the JSON estimate."""
    mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    with open(image_path, "rb") as f:
        data_url = f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": FOOD_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        temperature=0.2,
    )
    text = resp.choices[0].message.content
    # Reasoning models (Qwen3.x) may prepend <think>...</think>; models often
    # also wrap JSON in ```json fences. Keep only the object.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return json.loads(text[text.find("{") : text.rfind("}") + 1])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Chat or analyse a food photo with one model")
    ap.add_argument("image", nargs="?", help="food photo; omit it for chat mode")
    ap.add_argument("-p", "--provider", choices=PROVIDERS, default=os.getenv("AI_PROVIDER", "groq"))
    ap.add_argument("-m", "--model", default=os.getenv("AI_MODEL"),
                    help="override the provider's default model")
    args = ap.parse_args()

    use(args.provider, args.model)
    print(f"[{args.provider} / {MODEL}]", file=sys.stderr)

    if args.image:
        print(json.dumps(analyze_food(args.image), ensure_ascii=False, indent=2))
    else:
        history: list[dict] = []
        while (q := input("Bạn: ").strip()) not in ("", "exit"):
            print("AI:", chat(history, q))