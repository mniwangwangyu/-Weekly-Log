import requests
import os

# 1. 配置环境
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_PAGE_ID"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def get_all_pages():
    """获取数据库中所有的页面，按编辑时间倒序排列"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    # 排序：最后编辑时间从新到旧
    payload = {
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]
    }
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        return res.json().get("results", [])
    print(f"查询数据库失败: {res.text}")
    return []

def get_blocks(block_id):
    """获取页面正文内容"""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
    res = requests.get(url, headers=headers)
    return res.json().get("results", [])

def parse_blocks(blocks):
    """解析正文块"""
    md = []
    for block in blocks:
        block_type = block["type"]
        # 仅抓取文本段落，你可以根据需要增加对列表、图片的解析
        if block_type == "paragraph":
            rich_texts = block["paragraph"]["rich_text"]
            if rich_texts:
                md.append(rich_texts[0]["plain_text"])
    return "\n\n".join(md)

def update_readme(full_content):
    """全量更新 README 中的周报区域"""
    with open("README.md", "r", encoding="utf-8") as f:
        text = f.read()

    start_tag = ""
    end_tag = ""
    
    try:
        start_idx = text.index(start_tag) + len(start_tag)
        end_idx = text.index(end_tag)
    except ValueError:
        print("错误：README.md 中未找到同步标签！")
        return

    # 组装最终文本：保留标签前后的内容，中间全部换成最新的全量周报
    new_text = text[:start_idx] + "\n" + full_content + "\n" + text[end_idx:]

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_text)

# --- 主程序 ---
print("开始全量同步 Notion 数据库...")
pages = get_all_pages()
all_articles_md = []

for page in pages:
    # 获取标题
    props = page["properties"]
    title_obj = props.get("Name") or props.get("标题") or props.get("title")
    title = title_obj["title"][0]["plain_text"] if title_obj["title"] else "未命名"
    
    print(f"正在抓取内容: {title}")
    
    # 获取该页面的正文
    blocks = get_blocks(page["id"])
    content = parse_blocks(blocks)
    
    # 格式化单篇周报
    article_md = f"### 📅 {title}\n{content}\n\n---"
    all_articles_md.append(article_md)

# 合并所有周报并写入
if all_articles_md:
    full_md = "\n\n".join(all_articles_md)
    update_readme(full_md)
    print(f"✅ 成功同步了 {len(all_articles_md)} 篇周报！")
else:
    print("❌ 数据库里没找到任何内容。")
