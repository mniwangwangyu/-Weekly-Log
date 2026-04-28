import requests
import os
from urllib.parse import urlparse

# 1. 配置环境
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_PAGE_ID"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def get_latest_page():
    """从数据库获取最后编辑的一篇文章"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        "page_size": 1
    }
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        results = res.json().get("results", [])
        if results:
            page_id = results[0]["id"]
            # 兼容不同的标题属性名，通常是 Name 或 标题
            props = results[0]["properties"]
            title_obj = props.get("Name") or props.get("标题") or props.get("title")
            title = title_obj["title"][0]["plain_text"] if title_obj["title"] else "未命名周报"
            return page_id, title
    print(f"查询数据库失败: {res.text}")
    return None, None

def get_blocks(block_id):
    """获取页面内的具体内容"""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
    res = requests.get(url, headers=headers)
    return res.json().get("results", [])

def parse_blocks(blocks):
    """解析 Notion 块为 Markdown"""
    md = []
    for block in blocks:
        block_type = block["type"]
        if block_type == "paragraph":
            rich_texts = block["paragraph"]["rich_text"]
            if rich_texts:
                md.append(rich_texts[0]["plain_text"])
        elif block_type == "heading_1":
            md.append(f"# {block['heading_1']['rich_text'][0]['plain_text']}")
        elif block_type == "heading_2":
            md.append(f"## {block['heading_2']['rich_text'][0]['plain_text']}")
        elif block_type == "bulleted_list_item":
            md.append(f"* {block['bulleted_list_item']['rich_text'][0]['plain_text']}")
    return "\n\n".join(md)

def update_readme(new_content, title):
    """核心逻辑：在固定区域内追加内容，并保持排序"""
    with open("README.md", "r", encoding="utf-8") as f:
        text = f.read()

    start_tag = ""
    end_tag = ""
    
    try:
        start_idx = text.index(start_tag) + len(start_tag)
        end_idx = text.index(end_tag)
    except ValueError:
        print("错误：README.md 中未找到同步暗号标签！")
        return

    # 获取暗号中间已有的旧内容
    existing_content = text[start_idx:end_idx].strip()
    
    # 🔍 重要：检查这篇周报是否已经同步过，防止重复追加
    if title in existing_content:
        print(f"⚠️ 周报 '{title}' 已经存在于 README 中，跳过更新。")
        return

    # 组装：新标题 + 新内容 + 分割线 + 旧内容
    # 这样每次更新都会排在最上面，旧的往下排
    header = f"\n\n### 📅 {title}"
    combined_content = f"{header}\n{new_content}\n\n---\n{existing_content}"
    
    final_text = text[:start_idx] + "\n" + combined_content.strip() + "\n\n" + text[end_idx:]

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(final_text)

# 执行主流程
page_id, title = get_latest_page()
if page_id:
    print(f"🚀 发现最新内容: {title}")
    blocks = get_blocks(page_id)
    markdown_content = parse_blocks(blocks)
    update_readme(markdown_content, title)
    print("✅ 同步完成！")
else:
    print("❌ 未能获取到有效的周报页面。")
