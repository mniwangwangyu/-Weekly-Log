import requests
import os
from urllib.parse import urlparse

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["NOTION_PAGE_ID"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
}

# 获取 block
def get_blocks(block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
    res = requests.get(url, headers=headers)
    return res.json()["results"]

# 下载图片
def download_image(url, path):
    r = requests.get(url)
    if r.status_code == 200:
        with open(path, "wb") as f:
            f.write(r.content)

# 解析 Notion → Markdown
def parse_blocks(blocks):
    md = []
    img_dir = "images"
    os.makedirs(img_dir, exist_ok=True)

    img_index = 1

    for block in blocks:
        t = block["type"]

        # 文本
        if t == "paragraph":
            texts = block[t]["rich_text"]
            line = "".join([t["plain_text"] for t in texts])
            md.append(line)

        # 标题
        elif t == "heading_2":
            texts = block[t]["rich_text"]
            line = "".join([t["plain_text"] for t in texts])
            md.append(f"## {line}")

        # 图片
        elif t == "image":
            img = block["image"]

            if img["type"] == "external":
                url = img["external"]["url"]
            else:
                url = img["file"]["url"]

            ext = os.path.splitext(urlparse(url).path)[-1] or ".png"
            filename = f"img_{img_index}{ext}"
            filepath = os.path.join(img_dir, filename)

            download_image(url, filepath)

            md.append(f"![img](images/{filename})")

            img_index += 1

    return "\n\n".join(md)

# 更新 README 指定区域
def update_readme(content):
    with open("README.md", "r", encoding="utf-8") as f:
        text = f.read()

    start_tag = "<!-- WEEKLY-REPORT-START -->"
    end_tag = "<!-- WEEKLY-REPORT-END -->"

    start = text.index(start_tag) + len(start_tag)
    end = text.index(end_tag)

    new_text = text[:start] + "\n\n" + content + "\n\n" + text[end:]

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_text)

# 主流程
blocks = get_blocks(PAGE_ID)
content = parse_blocks(blocks)

update_readme(content)

print("done")
