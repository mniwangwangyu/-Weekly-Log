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
    """
    【设计师专用压缩逻辑】
    目标：减小像素尺寸，降低文件体积，同时保持渲染图质感。
    """
    if not url: return None
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', '_', filename_prefix)
        path = os.path.join(IMAGE_DIR, f"{clean_name}_{index}.webp")
        
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content))
            
            # --- 核心：像素压缩逻辑 ---
            # 设置最大宽度为 1200px。
            # 理由：GitHub README 展示区域宽度有限，1200px 足够在 Retina 屏幕上清晰显示，
            # 且体积只有 4K 原图的几分之一。
            target_width = 1200 
            if img.width > target_width:
                w_percent = (target_width / float(img.width))
                h_size = int((float(img.height) * float(w_percent)))
                # 使用 LANCZOS 算法，这是 Pillow 里缩放效果最锐利、细节保留最好的算法
                img = img.resize((target_width, h_size), Image.Resampling.LANCZOS)
            
            # 自动处理色彩模式
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # 使用 WebP 格式保存。quality=80 是黄金分割点：
            # 既能大幅度压缩体积，又不会出现你担心的“脏色块”。
            img.save(path, "WEBP", quality=80, method=6, optimize=True)
            return path
    except Exception as e:
        print(f"图片压缩失败: {e}")
    return None

def fetch_content(block_id):
    """递归抓取页面内容"""
    contents = ""
    img_idx = 0
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    try:
        blocks = requests.get(url, headers=headers).json().get("results", [])
        for block in blocks:
            b_type = block.get("type")
            if b_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                prefix = "### " if b_type == "heading_1" else "#### " if b_type == "heading_2" else ""
                text = "".join([t.get("plain_text", "") for t in block.get(b_type, {}).get("rich_text", [])])
                if text: contents += f"{prefix}{text}\n\n"
            elif b_type == "image":
                img_idx += 1
                img_url = block.get("image", {}).get("file", {}).get("url") or \
                          block.get("image", {}).get("external", {}).get("url")
                if img_url:
                    path = download_and_compress(img_url, f"p_{block_id[:4]}", img_idx)
                    if path: contents += f"![work]({path})\n\n"
        return contents
    except: return ""

def main():
    print("🚀 启动轻量化同步...")
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    pages = res.json().get("results", [])
    
    all_html = []
    for page in pages:
        props = page.get("properties", {})
        title = "未命名"
        for p in props.values():
            if p.get("type") == "title" and p.get("title"):
                title = p["title"][0]["plain_text"]; break
        
        detail = fetch_content(page["id"])
        # 折叠框确保 README 干净整洁
        section = f"<details><summary><b>📂 {title}</b></summary>\n\n{detail}\n<hr/></details>"
        all_html.append(section)

    with open("README.md", "r", encoding="utf-8") as f: text = f.read()
    start_tag, end_tag = "[HERE_START]", "[HERE_END]"
    if start_tag in text and end_tag in text:
        content_str = "\n\n".join(all_html)
        pattern = f"{re.escape(start_tag)}.*?{re.escape(end_tag)}"
        final_text = re.sub(pattern, f"{start_tag}\n\n{content_str}\n\n{end_tag}", text, flags=re.DOTALL)
        with open("README.md", "w", encoding="utf-8") as f: f.write(final_text)
        print("✅ 瘦身同步完成！")

if __name__ == "__main__": main()
