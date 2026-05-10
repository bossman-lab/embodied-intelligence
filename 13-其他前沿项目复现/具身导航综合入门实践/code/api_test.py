from openai import OpenAI
import base64
client = OpenAI(
    api_key="your-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 本地图片路径
image_path = "/home/robot/every_embodied_navigation/dog.webp"
# image_path = "/home/robot/every_embodied_navigation/dog.png"

# 转为Base64
with open(image_path, "rb") as f:
    base64_data = base64.b64encode(f.read()).decode("utf-8")

# 拼接成通义千问支持的格式
base64_url = f"data:image/webp;base64,{base64_data}"
# base64_url = f"data:image/png;base64,{base64_data}"

# 发送请求
completion = client.chat.completions.create(
    model="qwen3-vl-8b-instruct",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": base64_url}
                },
                {"type": "text", "text": "图中描绘的是什么景象?"}
            ]
        }
    ],
)

print(completion.choices[0].message.content)