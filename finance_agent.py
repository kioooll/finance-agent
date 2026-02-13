#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融资讯自动化分析脚本 (Map-Reduce 最终增强版)
功能：抓取 RSS 源 -> 分批 AI 摘要 (Map) -> 最终汇总分析 (Reduce) -> 飞书推送
修复：北京时间显示、9小时窗口、严格限制 AI 发挥、分批处理日志
"""

import os
import re
import json
import time
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import feedparser
import requests
from bs4 import BeautifulSoup


class FinanceAgent:
    """金融资讯自动化分析代理"""
    
    def __init__(self):
        """初始化配置"""
        # RSS 源配置
        self.rss_sources = [
            {"name": "财联社-深度", "url": "https://rsshub.app/cls/depth"},
            {"name": "财联社-热门", "url": "https://rsshub.app/cls/hot"},
            {"name": "华尔街见闻-最新", "url": "https://rsshub.app/wallstreetcn/news"},
            {"name": "华尔街见闻-最热", "url": "https://rsshub.app/wallstreetcn/hot"},
            {"name": "彭博社", "url": "https://news.google.com/rss/search?q=when:12h+source:Bloomberg"},
        ]
        
        # AI API 配置
        # 建议直接在代码里写死你的模型名，防止环境变量没设置导致默认用 gpt-4
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini") # <--- 这里改成你常用的便宜模型
        self.base_url = os.getenv("AI_BASE_URL", "")
        self.api_key = os.getenv("AI_API_KEY", "")
        
        # 飞书 Webhook 配置
        self.feishu_webhook = os.getenv("FEISHU_WEBHOOK", "")
        
        # 【修改点1】时效性：改为提取过去 9 小时的内容
        self.time_threshold = datetime.now() - timedelta(hours=9)
        
    def fetch_rss_feeds(self) -> List[Dict]:
        """抓取所有 RSS 源的内容"""
        all_articles = []
        
        for source in self.rss_sources:
            try:
                print(f"正在抓取: {source['name']}")
                feed = feedparser.parse(source['url'])
                
                for entry in feed.entries:
                    published_time = self._parse_publish_time(entry)
                    if published_time and published_time >= self.time_threshold:
                        article = {
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                            "published": published_time,
                            "summary": entry.get("summary", ""),
                            "source": source['name']
                        }
                        all_articles.append(article)
                time.sleep(1)
            except Exception as e:
                print(f"抓取 {source['name']} 失败: {str(e)}")
                continue
        
        all_articles.sort(key=lambda x: x['published'], reverse=True)
        return all_articles
    
    def _parse_publish_time(self, entry) -> Optional[datetime]:
        """解析发布时间"""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'published'):
                from email.utils import parsedate_tz
                time_tuple = parsedate_tz(entry.published)
                if time_tuple:
                    import time as time_module
                    timestamp = time_module.mktime(time_tuple[:9])
                    return datetime.fromtimestamp(timestamp)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except Exception as e:
            print(f"解析时间失败: {str(e)}")
        return None
    
    def clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ""
        soup = BeautifulSoup(text, 'html.parser')
        cleaned = soup.get_text(separator=' ', strip=True)
        cleaned = re.sub(r'https?://[^\s]+(?:广告|推广|点击|注册)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[.*?广告.*?\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def filter_articles(self, articles: List[Dict]) -> List[Dict]:
        """过滤文章"""
        filtered = []
        for article in articles:
            content = f"{article['title']} {article['summary']}"
            cleaned_content = self.clean_text(content)
            if len(cleaned_content) > 400:
                cleaned_content = cleaned_content[:400]
            if len(cleaned_content) >= 15:
                article['cleaned_content'] = cleaned_content
                filtered.append(article)
        return filtered

    def format_to_markdown(self, articles: List[Dict]) -> str:
        """格式化为 Markdown"""
        markdown_lines = []
        for article in articles:
            markdown_lines.append(f"## {article['title']}")
            markdown_lines.append(f"**来源**: {article['source']} | **时间**: {article['published'].strftime('%H:%M')}")
            markdown_lines.append(f"{article['cleaned_content']}\n")
            markdown_lines.append("---\n")
        return "\n".join(markdown_lines)
    
    def call_ai_api(self, prompt: str) -> Optional[str]:
        """调用 AI API"""
        if not self.api_key or not self.base_url:
            print("警告: AI API 配置未设置")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是冷静、客观的金融分析师。你的任务是基于提供的新闻进行事实总结，不进行发散性预测。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3, # 【修改点2】调低温度，让 AI 更老实
                "max_tokens": 4096
            }

            base = (self.base_url or "").strip().rstrip("/")
            if base.endswith("/v1"):
                base = base[:-3]
            url = f"{base}/v1/chat/completions"

            # 保持 300 秒超时
            response = requests.post(url, headers=headers, json=payload, timeout=300)
            
            if response.status_code == 200:
                return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                print(f"AI API 调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"AI API 调用异常: {str(e)}")
            return None
    
    def analyze_with_map_reduce(self, articles: List[Dict]) -> str:
        """Map-Reduce 分析主逻辑"""
        if not articles:
            return "无有效新闻。"

        # --- Map 阶段 ---
        batch_size = 10
        total_articles = len(articles)
        total_batches = math.ceil(total_articles / batch_size)
        
        print(f"\n🔄 进入 Map 阶段：共 {total_articles} 条新闻，分 {total_batches} 组处理")
        batch_summaries = []
        
        for i in range(total_batches):
            print(f"⚡ 正在处理第 {i + 1}/{total_batches} 组新闻...")
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, total_articles)
            current_batch = articles[start_idx:end_idx]
            batch_content = self.format_to_markdown(current_batch)
            
            # Map Prompt: 快速提取
            map_prompt = f"""请快速阅读以下新闻，提取核心事件和潜在的利好/利空逻辑线索。
要求：仅罗列事实，不要废话，不要发散。
新闻：
{batch_content}
"""
            summary = self.call_ai_api(map_prompt)
            if summary:
                batch_summaries.append(summary)

        if not batch_summaries:
            return "所有批次分析均失败。"

        # --- Reduce 阶段 ---
        print(f"\n🔄 进入 Reduce 阶段：汇总 {len(batch_summaries)} 份摘要...")
        combined_summaries = "\n".join(batch_summaries)
        
        # 【修改点3】最终 Prompt：严格限制内容和字数
        reduce_prompt = f"""基于以下资讯线索，生成一份简报。

【严格约束】
1. **必须完全基于提供的新闻内容**，严禁使用外部知识或进行没有依据的联想（AI Free Style）。
2. 内容要精炼，不要长篇大论。
3. **不要**提供泛泛的“投资建议”章节。

【输出格式】
### [9小时要闻总结]
(列出3-5条核心事件，每条不超过50字)

### [主线题材研判]
**核心题材**：(仅限一个最强题材)
**上涨逻辑拆解**：(仅根据新闻事实，简述为什么利好。分点说明，总字数控制在300字以内)

资讯线索：
{combined_summaries}
"""
        final_result = self.call_ai_api(reduce_prompt)
        return final_result if final_result else "汇总分析失败。"

    def send_to_feishu(self, content: str):
        """推送飞书"""
        if not self.feishu_webhook:
            print("警告: 飞书 Webhook 未配置")
            return
        
        try:
            max_len = 4000
            text = content or ""
            parts = []
            if len(text) <= max_len:
                parts = [text]
            else:
                # 简单分段逻辑
                for i in range(0, len(text), max_len):
                    parts.append(text[i:i+max_len])

            total = len(parts)
            for idx, part in enumerate(parts, 1):
                suffix = "" if total == 1 else f" ({idx}/{total})"
                payload = {
                    "msg_type": "interactive",
                    "card": {
                        "header": {
                            "title": {"tag": "plain_text", "content": f"📊 9小时风口研报{suffix}"},
                            "template": "blue"
                        },
                        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": part}}]
                    }
                }
                requests.post(self.feishu_webhook, json=payload, timeout=30)
                print(f"✅ 飞书推送成功 ({idx}/{total})")
                
        except Exception as e:
            print(f"飞书推送异常: {str(e)}")

    def run(self):
        """主执行流程"""
        print("=" * 50)
        print("🚀 金融资讯自动化分析 (Map-Reduce 修复版) 开始")
        print("=" * 50)
        
        # 1. 抓取
        print("\n📡 步骤 1: 抓取 RSS 源...")
        articles = self.fetch_rss_feeds()
        print(f"✅ 共抓取 {len(articles)} 篇文章")
        
        if not articles:
            print("⚠️ 无内容，退出")
            return
        
        # 2. 过滤
        print("\n🧹 步骤 2: 清洗和过滤...")
        filtered_articles = self.filter_articles(articles)
        
        if not filtered_articles:
            print("⚠️ 无有效内容，退出")
            return

        # 3. AI 分析
        print("\n🤖 步骤 3: Map-Reduce AI 分析中...")
        analysis_result = self.analyze_with_map_reduce(filtered_articles)
        
        # 【修改点4】时间修正：GitHub是UTC，这里强制+8小时转为北京时间
        beijing_time = (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
        
        final_content = f"""## 📊 9小时金融资讯分析报告

{analysis_result}

---
*报告生成时间: {beijing_time} (北京时间)*
"""
        
        # 4. 推送
        print("\n📤 步骤 4: 推送到飞书...")
        self.send_to_feishu(final_content)
        
        print("\n✅ 任务完成！")

def main():
    agent = FinanceAgent()
    agent.run()

if __name__ == "__main__":
    main()
