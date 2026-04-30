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
    """【设计师专用】高质量图片处理"""
    if not url: return None
    try:
        # 兼容中文文件名并防止特殊字符导致路径报错
        clean_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', '_', filename_prefix)
        path = os.path.join(IMAGE_DIR, f"{clean_name}_{index}.webp")
        
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content))
            
            # 保持原始比例缩放，不拉伸
            max_width = 1600 # 提升到 1600 宽，保证 3D 细节清晰
            if img.width > max_width:
                w_percent = (max_width / float(img.width))
                h_size = int((float(img.height) * float(w_percent)))
                img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
            
            # 自动处理颜色空间，防止渲染图变色
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            # 提高质量到 90，确保泰山纹理不模糊
            img.save(path, "WEBP", quality=90, optimize=True)
            return path
    except Exception as e:
        print(f"图片下载失败: {e}")
    return None

def fetch_all_blocks(block_id):
    """递归抓取页面内所有内容，包括文字和多张图"""
    contents = ""
    img_idx = 0
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    
    try:
        res = requests.get(url, headers=headers)
        blocks = res.json().get("results", [])
        
        for block in blocks:
            b_type = block.get("type")
            # 1. 提取文字和标题
            if b_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                rich_text = block.get(b_type, {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    prefix = "### " if b_type == "heading_1" else "#### " if b_type == "heading_2" else ""
                    contents += f"{prefix}{text}\n\n"
            
            # 2. 提取所有图片（关键：不仅仅是第一张）
            elif b_type == "image":
                img_idx += 1
                img_data = block.get("image", {})
                img_url = img_data.get("file", {}).get("url") or img_data.get("external", {}).get("url")
                if img_url:
                    # 使用页面 ID 或索引防止重名
                    local_path = download_and_compress(img_url, f"img_{block_id[:5]}", img_idx)
                    if local_path:
                        contents += f"![design_work]({local_path})\n\n"
        return contents
    except:
        return "*(内容提取失败)*"

def main():
    print("🚀 启动全量内容同步...")
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    pages = res.json().get("results", [])
    
    all_html = []
    for page in pages:
        # 获取 Notion 标题
        props = page.get("properties", {})
        title = "未命名项目"
        for p in props.values():
            if p.get("type") == "title" and p.get("title"):
                title = p["title"][0]["plain_text"]
                break
        
        # 抓取页面内完整内容
        detail_markdown = fetch_all_blocks(page["id"])
        
        # 封装进折叠框
        section = f"<details>\n<summary><b>📂 {title} (点击展开完整详情)</b></summary>\n\n"
        section += detail_markdown
        section += "\n<hr/></details>"
        all_html.append(section)

    # 写入 README
    with open("README.md", "r", encoding="utf-8") as f: text = f.read()
    start_tag, end_tag = "[HERE_START]", "[HERE_END]"
    
    if start_tag in text and end_tag in text:
        content_str = "\n\n".join(all_html)
        pattern = f"{re.escape(start_tag)}.*?{re.escape(end_tag)}"
        final_text = re.sub(pattern, f"{start_tag}\n\n{content_str}\n\n{end_tag}", text, flags=re.DOTALL)
        with open("README.md", "w", encoding="utf-8") as f: f.write(final_text)
        print("✅ 同步圆满完成！内容、文字、图集已全部折叠。")

if __name__ == "__main__": main()
