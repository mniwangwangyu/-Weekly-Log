import os, requests, re
from PIL import Image
from io import BytesIO

# 1. 基础配置
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_PAGE_ID")
IMAGE_DIR = "images"
headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)

def download_and_compress(url, filename):
    if not url: return None
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', '_', filename)
        path = os.path.join(IMAGE_DIR, f"{clean_name}.webp")
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGB")
            if img.width > 1200: img = img.resize((1200, int(1200/img.width*img.height)), Image.LANCZOS)
            img.save(path, "WEBP", quality=75)
            return path
    except: return None
    return None

def main():
    print("🚀 正在从 Notion 搬运周报...")
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    if res.status_code != 200: return print(f"❌ API 错误: {res.text}")
    
    pages = res.json().get("results", [])
    if not pages: return print("❌ 数据库是空的或 ID 不对")

    all_html = []
    for page in pages:
        props = page.get("properties", {})
        
        # 1. 安全抓取标题
        title = "未命名周报"
        for p_val in props.values():
            if p_val.get("type") == "title" and p_val.get("title"):
                title = p_val["title"][0]["plain_text"]
                break
        
        # 2. 安全抓取图片 (加了三层 None 检查)
        img_url = None
        cover = page.get("cover")
        if cover:
            img_url = cover.get("external", {}).get("url") or cover.get("file", {}).get("url")
        
        # 如果没封面，钻进页面找第一张图
        if not img_url:
            try:
                block_res = requests.get(f"https://api.notion.com/v1/blocks/{page['id']}/children", headers=headers)
                for b in block_res.json().get("results", []):
                    if b.get("type") == "image":
                        img_obj = b.get("image", {})
                        img_url = img_obj.get("file", {}).get("url") or img_obj.get("external", {}).get("url")
                        break
            except: pass

        img_path = download_and_compress(img_url, title)

        # 3. 构造 HTML
        html = f"<details>\n<summary><b>📅 {title}</b></summary>\n\n"
        if img_path: 
            html += f"![{title}]({img_path})\n\n"
        else: 
            html += "*(暂无图片预览)*\n\n"
        html += "<hr/></details>"
        all_html.append(html)

    # 4. 写入 README
    with open("README.md", "r", encoding="utf-8") as f: text = f.read()
    start_tag, end_tag = "[HERE_START]", "[HERE_END]"
    
    if start_tag in text and end_tag in text:
        new_content = "\n\n".join(all_html)
        pattern = f"{re.escape(start_tag)}.*?{re.escape(end_tag)}"
        final_text = re.sub(pattern, f"{start_tag}\n\n{new_content}\n\n{end_tag}", text, flags=re.DOTALL)
        with open("README.md", "w", encoding="utf-8") as f: f.write(final_text)
        print("✅ README 同步成功！")
    else:
        print("❌ 找不到暗号")

if __name__ == "__main__": main()
