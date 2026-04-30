import os
import requests
import re
from PIL import Image
from io import BytesIO

# 1. 配置加载
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_PAGE_ID")
IMAGE_DIR = "images"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def get_all_pages():
    """获取所有页面并加入容错"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    try:
        res = requests.post(url, headers=headers, timeout=15)
        res.raise_for_status()
        return res.json().get("results", [])
    except Exception as e:
        print(f"获取页面失败: {e}")
        return []

def download_and_compress_image(url, filename):
    """工业设计渲染图专用压缩：WebP 格式"""
    try:
        clean_name = re.sub(r'[\\/:*?"<>|]', '_', filename)
        local_path = os.path.join(IMAGE_DIR, f"{clean_name}.webp")
        
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content))
            # 自动处理颜色模式转换
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            # 限制宽度为 1200px (足够清晰且轻量)
            if img.width > 1200:
                h = int((1200 / img.width) * img.height)
                img = img.resize((1200, h), Image.Resampling.LANCZOS)
            img.save(local_path, "WEBP", quality=75, optimize=True)
            return local_path
    except Exception as e:
        print(f"图片处理失败: {e}")
    return None

def main():
    pages = get_all_pages()
    if not pages:
        print("未找到有效页面。")
        return

    all_articles_html = []
    
    for page in pages:
        # 安全获取标题
        props = page.get("properties", {})
        title_list = props.get("Name", {}).get("title", []) or props.get("标题", {}).get("title", [])
        title = title_list[0]["plain_text"] if title_list else "未命名项目"
        
        # 安全获取封面图 (关键修复点！)
        cover_data = page.get('cover')
        cover_url = None
        if cover_data:
            cover_url = cover_data.get('external', {}).get('url') or cover_data.get('file', {}).get('url')
        
        img_path = ""
        if cover_url:
            img_path = download_and_compress_image(cover_url, title)

        # 生成符合你 README 要求的 HTML 结构
        content = f"<details><summary><b>📅 {title} (点击查看压缩预览)</b></summary>\n\n"
        if img_path:
            # 这里的链接使用 GitHub 的相对路径
            content += f"![{title}]({img_path})\n\n"
        content += "<hr/></details>"
        all_articles_html.append(content)

    # 写入 README (对接你的 [HERE_START] 暗号)
    with open("README.md", "r", encoding="utf-8") as f:
        text = f.read()

    start_tag, end_tag = "[HERE_START]", "[HERE_END]"
    if start_tag in text and end_tag in text:
        pre = text.split(start_tag)[0]
        post = text.split(end_tag)[-1]
        new_text = f"{pre}{start_tag}\n\n" + "\n\n".join(all_articles_html) + f"\n\n{end_tag}{post}"
        
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new_text)
        print("✅ 压缩版同步完成！")
    else:
        print("❌ 找不到暗号标记。")

if __name__ == "__main__":
    main()
