import os, requests, re
from PIL import Image
from io import BytesIO

# 1. 基础配置
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_PAGE_ID")
IMAGE_DIR = "images"
headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)

def download_and_compress(url, filename_prefix, index):
    """处理页面内多张图片，确保不重名"""
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', '_', filename_prefix)
        path = os.path.join(IMAGE_DIR, f"{clean_name}_{index}.webp")
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGB")
            # 限制宽度为 1000px，兼顾手机端查看
            if img.width > 1000: img = img.resize((1000, int(1000/img.width*img.height)), Image.LANCZOS)
            img.save(path, "WEBP", quality=75)
            return path
    except: return None

def get_full_content(page_id, title):
    """关键：遍历页面内所有 Block，提取文字和图片"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    block_res = requests.get(url, headers=headers)
    blocks = block_res.json().get("results", [])
    
    markdown_content = ""
    img_idx = 0
    
    for block in blocks:
        b_type = block.get("type")
        
        # 提取文字块 (支持标题和普通段落)
        if b_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
            rich_texts = block.get(b_type, {}).get("rich_text", [])
            text = "".join([t.get("plain_text", "") for t in rich_texts])
            if text:
                prefix = "# " if b_type == "heading_1" else "## " if b_type == "heading_2" else "### " if b_type == "heading_3" else ""
                markdown_content += f"{prefix}{text}\n\n"
        
        # 提取图片块 (下载并压缩每一张)
        elif b_type == "image":
            img_idx += 1
            img_info = block.get("image", {})
            img_url = img_info.get("file", {}).get("url") or img_info.get("external", {}).get("url")
            if img_url:
                local_path = download_and_compress(img_url, title, img_idx)
                if local_path:
                    markdown_content += f"![image]({local_path})\n\n"
                    
    return markdown_content

def main():
    # 获取数据库列表
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    pages = res.json().get("results", [])
    if not pages: return print("❌ 数据库是空的")

    all_html = []
    for page in pages:
        # 1. 找标题
        title = "未命名周报"
        props = page.get("properties", {})
        for p in props.values():
            if p.get("type") == "title" and p.get("title"):
                title = p["title"][0]["plain_text"]
                break
        
        # 2. 抓取该页面下所有的内容
        print(f"📦 正在搬运: {title}...")
        detail_text = get_full_content(page["id"], title)

        # 3. 构造折叠 HTML 结构 (包含全量内容)
        html_block = f"<details>\n<summary><b>📅 {title} (点击查看完整记录)</b></summary>\n\n"
        html_block += detail_text
        html_block += "\n<hr/></details>"
        all_html.append(html_block)

    # 4. 写入 README
    with open("README.md", "r", encoding="utf-8") as f: text = f.read()
    start_tag, end_tag = "[HERE_START]", "[HERE_END]"
    
    if start_tag in text and end_tag in text:
        new_text = text.split(start_tag)[0] + start_tag + "\n\n" + "\n\n".join(all_html) + "\n\n" + end_tag + text.split(end_tag)[-1]
        with open("README.md", "w", encoding="utf-8") as f: f.write(new_text)
        print("✅ 同步成功！快去刷新 README 看看！")
    else:
        print("❌ 找不到暗号")

if __name__ == "__main__": main()
