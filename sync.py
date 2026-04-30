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
    """专门处理设计师的 4K 渲染图"""
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', '_', filename)
        path = os.path.join(IMAGE_DIR, f"{clean_name}.webp")
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGB")
            # 缩放到 1200 宽，兼顾清晰度和加载速度
            if img.width > 1200: img = img.resize((1200, int(1200/img.width*img.height)), Image.LANCZOS)
            img.save(path, "WEBP", quality=75)
            return path
    except: return None

def main():
    print("🚀 正在从 Notion 搬运周报...")
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    pages = res.json().get("results", [])
    if not pages: return print("❌ 没找到页面，请检查 DATABASE_ID")

    all_html = []
    for page in pages:
        props = page.get("properties", {})
        
        # --- 针对你的 Notion 修正：寻找名为 'Date' 的标题列 ---
        title = "未命名周报"
        # 自动探测标题列
        for p_name, p_val in props.items():
            if p_val.get("type") == "title" and p_val.get("title"):
                title = p_val["title"][0]["plain_text"]
                break
        
        # 寻找图片：先看封面图，再看页面内的第一张图
        img_url = page.get("cover", {}).get("external", {}).get("url") or \
                  page.get("cover", {}).get("file", {}).get("url")
        
        if not img_url:
            block_res = requests.get(f"https://api.notion.com/v1/blocks/{page['id']}/children", headers=headers)
            for b in block_res.json().get("results", []):
                if b["type"] == "image":
                    img_url = b["image"].get("file", {}).get("url") or b["image"].get("external", {}).get("url")
                    break

        img_path = download_and_compress(img_url, title) if img_url else None

        # 构造 HTML 折叠块
        html = f"<details>\n<summary><b>📅 {title} (点击查看)</b></summary>\n\n"
        if img_path: html += f"![{title}]({img_path})\n\n"
        else: html += "*(此周报暂无图片预览)*\n\n"
        html += "<hr/></details>"
        all_html.append(html)

    # --- 写入 README：精准匹配你的暗号 ---
    with open("README.md", "r", encoding="utf-8") as f: text = f.read()
    start_tag, end_tag = "[HERE_START]", "[HERE_END]"
    
    if start_tag in text and end_tag in text:
        new_content = "\n\n".join(all_html)
        pattern = f"{re.escape(start_tag)}.*?{re.escape(end_tag)}"
        final_text = re.sub(pattern, f"{start_tag}\n\n{new_content}\n\n{end_tag}", text, flags=re.DOTALL)
        with open("README.md", "w", encoding="utf-8") as f: f.write(final_text)
        print("✅ README 已更新！")
    else:
        print("❌ 找不到 [HERE_START] 暗号，请检查 README")

if __name__ == "__main__": main()
