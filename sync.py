import requests
import os

# 1. 配置环境
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
    if not os.path.exists("images"):
        os.makedirs("images")
    filepath = os.path.join("images", filename)
    try:
        res = requests.get(url, stream=True)
        if res.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in res.iter_content(1024):
                    f.write(chunk)
            return filepath
    except:
        pass
    return None

def parse_blocks(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url, headers=headers)
    blocks = res.json().get("results", [])
    md = []
    img_count = 0
    for block in blocks:
        b_type = block["type"]
        if b_type == "paragraph":
            rich_texts = block["paragraph"]["rich_text"]
            if rich_texts:
                md.append(rich_texts[0]["plain_text"])
        elif b_type == "image":
            img_count += 1
            img_obj = block["image"]
            img_url = img_obj["file"]["url"] if "file" in img_obj else img_obj["external"]["url"]
            img_filename = f"notion_{page_id[:8]}_{img_count}.png"
            local_path = download_image(img_url, img_filename)
            if local_path:
                md.append(f"![image](images/{img_filename})")
    return "\n\n".join(md)

def update_readme(full_content):
    with open("README.md", "r", encoding="utf-8") as f:
        text = f.read()

    # 这里已经帮你填好了暗号，并且保证了缩进正确
    start_tag = ""
    end_tag = ""
    
    if start_tag in text and end_tag in text:
        start_idx = text.index(start_tag) + len(start_tag)
        end_idx = text.index(end_tag)
        new_text = text[:start_idx] + "\n\n" + full_content + "\n\n" + text[end_idx:]
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new_text)

# --- 主程序 ---
pages = get_all_pages()
all_md = []
for page in pages:
    props = page["properties"]
    title = "未命名"
    for p in props.values():
        if p["type"] == "title" and p["title"]:
            title = p["title"][0]["plain_text"]
            break
    print(f"正在抓取: {title}")
    content = parse_blocks(page["id"])
    if content.strip():
        all_md.append(f"### 📅 {title}\n{content}\n\n---")

if all_md:
    update_readme("\n\n".join(all_md))
    print("✅ 全部同步完成！")
