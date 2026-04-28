import requests
import os
import re
from PIL import Image  # 新增：图片处理库
from io import BytesIO

# 1. 配置
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_PAGE_ID"]
IMAGE_DIR = "images"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
}

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def download_and_compress_image(url, filename):
    """下载、压缩并保存图片"""
    try:
        clean_name = re.sub(r'[\\/:*?"<>|]', '_', filename)
        local_path = os.path.join(IMAGE_DIR, f"{clean_name}.webp") # 推荐用 webp 格式，体积更小
        
        r = requests.get(url)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content))
            
            # 1. 自动转换颜色模式（防止 CMYK 等模式报错）
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # 2. 限制最大宽度为 1200px (展示绰绰有余)
            max_width = 1200
            if img.width > max_width:
                height = int((max_width / img.width) * img.height)
                img = img.resize((max_width, height), Image.Resampling.LANCZOS)
            
            # 3. 压缩并保存为 webp (质量设为 75)
            img.save(local_path, "WEBP", quality=75, optimize=True)
            return local_path
    except Exception as e:
        print(f"压缩失败: {e}")
    return None

def parse_blocks(page_id, page_title):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url, headers=headers)
    blocks = res.json().get("results", [])
    md = []
    img_count = 0
    
    for block in blocks:
        b_type = block["type"]
        if b_type == "paragraph":
            texts = block["paragraph"]["rich_text"]
            if texts: md.append(texts[0]["plain_text"])
        elif b_type == "image":
            img_count += 1
            img_obj = block["image"]
            remote_url = img_obj["file"]["url"] if "file" in img_obj else img_obj["external"]["url"]
            
            local_name = f"{page_title}_{img_count}"
            local_path = download_and_compress_image(remote_url, local_name)
            if local_path:
                # 引用 GitHub 本地压缩后的图片
                md.append(f"![{page_title}](https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY')}/main/{local_path})")
    
    return "\n\n".join(md)

def update_readme(full_content):
    with open("README.md", "r", encoding="utf-8") as f:
        text = f.read()
    start_tag, end_tag = "[HERE_START]", "[HERE_END]"
    if start_tag in text and end_tag in text:
        pre = text.split(start_tag)[0]
        post = text.split(end_tag)[-1]
        new_text = f"{pre}{start_tag}\n\n{full_content.strip()}\n\n{end_tag}{post}"
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new_text)
        print("✅ 压缩版同步完成！")

# --- 主程序 ---
pages = get_all_pages()
all_articles = []
for page in pages:
    props = page["properties"]
    title = "未命名"
    for p in props.values():
        if p["type"] == "title" and p["title"]:
            title = p["title"][0]["plain_text"]
            break
    content = parse_blocks(page["id"], title)
    if content.strip():
        all_articles.append(f"<details><summary><b>📅 {title} (点击查看压缩预览)</b></summary>\n\n{content}\n\n<hr/></details>")

if all_articles:
    update_readme("\n".join(all_articles))
