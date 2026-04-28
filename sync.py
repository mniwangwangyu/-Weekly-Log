import requests
import os
import re

# 配置环境
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_PAGE_ID"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
}

def get_all_pages():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {"sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]}
    res = requests.post(url, json=payload, headers=headers)
    return res.json().get("results", []) if res.status_code == 200 else []

def download_image(url, filename):
    """将 Notion 里的临时图片下载到本地 images 文件夹"""
    if not os.path.exists("images"):
        os.makedirs("images")
    filepath = os.path.join("images", filename)
    res = requests.get(url, stream=True)
    if res.status_code == 200:
        with open(filepath, "wb") as f:
            for chunk in res.iter_content(1024):
                f.write(chunk)
        return filepath
    return None

def parse_blocks(page_id):
    """抓取文字和图片"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url, headers=headers)
    blocks = res.json().get("results", [])
    md = []
    img_count = 0

    for block in blocks:
        b_type = block["type"]
        # 处理文字
        if b_type == "paragraph":
            rich_texts = block["paragraph"]["rich_text"]
            if rich_texts:
                md.append(rich_texts[0]["plain_text"])
        
        # 处理图片
        elif b_type == "image":
            img_count += 1
            img_obj = block["image"]
            img_url = img_obj["file"]["url"] if "file" in img_obj else img_obj["external"]["url"]
            
            # 为图片生成唯一文件名
            clean_page_id = page_id.replace("-", "")[:8]
            img_filename = f"notion_{clean_page_id}_{img_count}.png"
            
            # 下载图片
            local_path = download_image(img_url, img_filename)
            if local_path:
                # 在 README 中插入相对路径链接
                md.append(f"![image](images/{img_filename})")
                
    return "\n\n".join(md)

def update_readme(full_content):
    with open("README.md", "r", encoding="utf-8") as f:
        text = f.read()

    start_tag = ""
    end_tag = ""
    
    if start_tag in text and end_tag in text:
        start_idx = text.index(start_tag) + len(start_tag)
        end_idx = text.index(end_tag)
        new_text = text[:start_idx] + "\n\n" + full_content + "\n\n" + text[end_idx:]
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new_text)

# 主程序
pages = get_all_pages()
all_md = []

for page in pages:
    props = page["properties"]
    title = "未命名"
    for p in props.values():
        if p["type"] == "title" and p["title"]:
            title = p["title"][0]["plain_text"]
            break
            
    print(f"正在同步: {title}")
    content = parse_blocks(page["id"])
    if content.strip():
        all_md.append(f"### 📅 {title}\n{content}\n\n---")

if all_md:
    update_readme("\n\n".join(all_md))
    print("✅ 同步完成（包含图片处理）")
