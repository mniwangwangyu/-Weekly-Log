import os
import requests
from PIL import Image
from io import BytesIO
import re

# 配置环境
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DATABASE_ID = os.getenv('NOTION_PAGE_ID')

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_all_pages():
    """获取 Notion 数据库中所有的周报页面"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    all_pages = []
    has_more = True
    start_cursor = None
    while has_more:
        payload = {"start_cursor": start_cursor} if start_cursor else {}
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code != 200: break
        data = res.json()
        all_pages.extend(data.get("results", []))
        has_more = data.get("has_more")
        start_cursor = data.get("next_cursor")
    return all_pages

def download_and_compress_img(url, filename):
    """关键：下载并将 4K 渲染图压缩为 WebP"""
    if not os.path.exists('images'): os.makedirs('images')
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            img = Image.open(BytesIO(res.content))
            path = f"images/{filename}.webp"
            # 保持 80 质量，体积缩小 90%
            img.save(path, "WEBP", quality=80)
            return path
    except: return None
    return None

def main():
    pages = get_all_pages()
    if not pages: return

    # README 的头部内容
    new_content = "# My Design Portfolio\n\n> 自动化周报系统已上线记录 AetherPet 等项目进度。\n\n"

    for index, page in enumerate(pages):
        # 获取标题（假设 Notion 属性名是 'Name'）
        title_list = page['properties'].get('Name', {}).get('title', [])
        title = title_list[0]['plain_text'] if title_list else f"Weekly Report {index}"
        
        # 获取封面图或页面内的第一张图
        cover_url = page.get('cover', {}).get('external', {}).get('url') or \
                    page.get('cover', {}).get('file', {}).get('url')
        
        img_path = ""
        if cover_url:
            img_filename = f"report_{index}"
            img_path = download_and_compress_img(cover_url, img_filename)

        # 核心：生成 HTML 折叠框结构
        new_content += f"<details>\n<summary>📅 {title} (点击展开详情)</summary>\n\n"
        if img_path:
            new_content += f"![{title}]({img_path})\n\n"
        new_content += "*(内容已由 Smart Bot 自动同步)*\n\n"
        new_content += "</details>\n\n"

    # 物理替换 README 中的内容
    with open("README.md", "r", encoding="utf-8") as f:
        old_readme = f.read()

    # 使用之前约定的分隔符逻辑
    start_marker = ""
    end_marker = ""
    
    if start_marker in old_readme and end_marker in old_readme:
        pattern = f"{start_marker}.*?{end_marker}"
        replacement = f"{start_marker}\n{new_content}\n{end_marker}"
        final_readme = re.sub(pattern, replacement, old_readme, flags=re.DOTALL)
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(final_readme)
        print("✅ 完美同步！")
    else:
        print("❌ 没在 README 里找到分隔符，请确保 README 包含那两行注释。")

if __name__ == "__main__":
    main()
