#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融资讯自动化分析脚本
功能：抓取 RSS 源 -> 清洗数据 -> AI 分析 -> 飞书推送
"""

import os
import re
import json
import time
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
        
        # AI API 配置（从环境变量读取）
        self.model = os.getenv("AI_MODEL", "gpt-4")
        self.base_url = os.getenv("AI_BASE_URL", "")
        self.api_key = os.getenv("AI_API_KEY", "")
        
        # 飞书 Webhook 配置
        self.feishu_webhook = os.getenv("FEISHU_WEBHOOK", "")
        
        # 时效性：仅提取过去 12 小时的内容
        self.time_threshold = datetime.now() - timedelta(hours=12)
        
    def fetch_rss_feeds(self) -> List[Dict]:
        """抓取所有 RSS 源的内容"""
        all_articles = []
        
        for source in self.rss_sources:
            try:
                print(f"正在抓取: {source['name']}")
                feed = feedparser.parse(source['url'])
                
                for entry in feed.entries:
                    # 解析发布时间
                    published_time = self._parse_publish_time(entry)
                    
                    # 只保留过去 12 小时的内容
                    if published_time and published_time >= self.time_threshold:
                        article = {
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                            "published": published_time,
                            "summary": entry.get("summary", ""),
                            "source": source['name']
                        }
                        all_articles.append(article)
                
                # 避免请求过快
                time.sleep(1)
                
            except Exception as e:
                print(f"抓取 {source['name']} 失败: {str(e)}")
                continue
        
        # 按发布时间倒序排列
        all_articles.sort(key=lambda x: x['published'], reverse=True)
        return all_articles
    
    def _parse_publish_time(self, entry) -> Optional[datetime]:
        """解析发布时间"""
        try:
            # feedparser 通常提供 published_parsed
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            # 备用方案：解析 published 字符串
            elif hasattr(entry, 'published'):
                from email.utils import parsedate_tz
                time_tuple = parsedate_tz(entry.published)
                if time_tuple:
                    import time as time_module
                    timestamp = time_module.mktime(time_tuple[:9])
                    return datetime.fromtimestamp(timestamp)
            # 如果都没有，尝试使用 updated_parsed
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except Exception as e:
            print(f"解析时间失败: {str(e)}")
        return None
    
    def clean_text(self, text: str) -> str:
        """清洗文本：去除广告链接和垃圾内容"""
        if not text:
            return ""
        
        # 使用 BeautifulSoup 去除 HTML 标签
        soup = BeautifulSoup(text, 'html.parser')
        cleaned = soup.get_text(separator=' ', strip=True)
        
        # 去除常见的广告链接模式
        cleaned = re.sub(r'https?://[^\s]+(?:广告|推广|点击|注册)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[.*?广告.*?\]', '', cleaned, flags=re.IGNORECASE)
        
        # 去除多余空白
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def filter_articles(self, articles: List[Dict]) -> List[Dict]:
        """过滤文章：去除少于 15 字的垃圾短讯"""
        filtered = []
        for article in articles:
            # 合并标题和摘要
            content = f"{article['title']} {article['summary']}"
            cleaned_content = self.clean_text(content)

            # 智能缩减：每篇文章的摘要（含标题）最多保留前 400 字符，避免单条过长
            if len(cleaned_content) > 400:
                cleaned_content = cleaned_content[:400]

            # 只保留内容长度 >= 15 字的文章
            if len(cleaned_content) >= 15:
                article['cleaned_content'] = cleaned_content
                filtered.append(article)

        return filtered

    def limit_input_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        输入端“防爆”逻辑：
        在合并为字符串前，先估算总字数；若超过 8,000 字，则仅保留时间戳最新的 15 条新闻摘要。
        不对字符串做硬截断，只通过减少文章数量控制长度。
        """
        if not articles:
            return articles

        # 假设 articles 已按发布时间倒序（最新在前）
        combined_text = "".join(a.get("cleaned_content", "") for a in articles)
        if len(combined_text) <= 8000 or len(articles) <= 15:
            return articles

        print("⚠️ 输入内容总长度超过 8000 字，仅保留最新 15 条新闻用于 AI 分析")
        return articles[:15]
    
    def format_to_markdown(self, articles: List[Dict]) -> str:
        """将所有内容整合为 Markdown 格式"""
        markdown_lines = ["# 金融资讯汇总（过去12小时）\n"]
        
        for article in articles:
            markdown_lines.append(f"## {article['title']}")
            markdown_lines.append(f"**来源**: {article['source']}")
            markdown_lines.append(f"**时间**: {article['published'].strftime('%Y-%m-%d %H:%M:%S')}")
            markdown_lines.append(f"**链接**: {article['link']}")
            markdown_lines.append(f"\n{article['cleaned_content']}\n")
            markdown_lines.append("---\n")
        
        return "\n".join(markdown_lines)
    
    def call_ai_api(self, prompt: str) -> Optional[str]:
        """调用 AI API 进行分析"""
        if not self.api_key or not self.base_url:
            print("警告: AI API 配置未设置，跳过 AI 分析")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建请求体（兼容 OpenAI / OpenAI 兼容中转 API）
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是顶尖对冲基金经理，擅长分析金融资讯并给出投资建议。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                # 输出限制：给 AI 足够的空间完整回答
                "max_tokens": 4096
            }

            # 兼容多种 base_url 形式，避免出现 /v1/v1 这种情况
            # 推荐：AI_BASE_URL 配置为类似 https://api.openai.com 或你的中转根地址
            base = (self.base_url or "").strip().rstrip("/")
            # 如果用户把 /v1 也写进去了，这里帮忙去掉一次，统一自己补 /v1
            if base.endswith("/v1"):
                base = base[:-3]

            url = f"{base}/v1/chat/completions"

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=300  # 对长文本分析增加超时时间到 300 秒
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                print(f"AI API 调用失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"AI API 调用异常: {str(e)}")
            return None
    
    def analyze_with_ai(self, markdown_content: str) -> str:
        """使用 AI 分析原始资料"""
        prompt = f"""你现在是顶尖对冲基金经理。请将提供的原始资料处理为两部分：



[12小时要闻总结]：用极简的 3-5 条 bullet points 告诉用户发生了什么重大事件，严禁废话。



[投资研判建议]：根据新闻逻辑，识别 1 个最可能的“主线题材”。注意：题材要细化（例如从“AI”细化到“AI算力租赁”），不能过于宽泛，并详细拆解其上涨逻辑。



原始资料：
{markdown_content}
"""

        analysis = self.call_ai_api(prompt)
        if analysis:
            return analysis
        else:
            return "AI 分析失败，请检查 API 配置。"
    
    def send_to_feishu(self, content: str):
        """通过飞书 Webhook 推送消息"""
        if not self.feishu_webhook:
            print("警告: 飞书 Webhook 未配置，跳过推送")
            return
        
        try:
            # 输出端“分段推送”逻辑：
            # 若内容超过 4000 字，自动拆分为 Part 1 / Part 2 / ... 依次推送
            max_len = 4000
            text = content or ""

            parts = []
            if len(text) <= max_len:
                parts = [text]
            else:
                start = 0
                total_length = len(text)
                while start < total_length:
                    end = min(total_length, start + max_len)
                    # 优先在当前段内寻找一个合适的换行作为分割点，避免打断 Markdown 结构
                    split_pos = text.rfind("\n", start, end)
                    if split_pos == -1 or split_pos <= start + max_len * 0.5:
                        split_pos = end
                    parts.append(text[start:split_pos])
                    start = split_pos

            total_parts = len(parts)

            for idx, part in enumerate(parts, start=1):
                suffix = "" if total_parts == 1 else f" - Part {idx}/{total_parts}"

                payload = {
                    "msg_type": "interactive",
                    "card": {
                        "config": {
                            "wide_screen_mode": True
                        },
                        "header": {
                            "title": {
                                "tag": "plain_text",
                                "content": f"📊 金融资讯分析报告{suffix}"
                            },
                            "template": "blue"
                        },
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "tag": "lark_md",
                                    "content": part
                                }
                            }
                        ]
                    }
                }

                response = requests.post(
                    self.feishu_webhook,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    print(f"✅ 飞书推送成功（{idx}/{total_parts}）")
                else:
                    print(f"❌ 飞书推送失败（{idx}/{total_parts}）: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ 飞书推送异常: {str(e)}")
    
    def run(self):
        """主执行流程"""
        print("=" * 50)
        print("🚀 金融资讯自动化分析开始")
        print("=" * 50)
        
        # 1. 抓取 RSS 源
        print("\n📡 步骤 1: 抓取 RSS 源...")
        articles = self.fetch_rss_feeds()
        print(f"✅ 共抓取 {len(articles)} 篇文章")
        
        if not articles:
            print("⚠️ 没有找到符合条件的内容，退出")
            return
        
        # 2. 过滤和清洗
        print("\n🧹 步骤 2: 清洗和过滤内容...")
        filtered_articles = self.filter_articles(articles)
        print(f"✅ 过滤后剩余 {len(filtered_articles)} 篇文章")
        
        if not filtered_articles:
            print("⚠️ 过滤后没有有效内容，退出")
            return

        # 2.5 输入端“防爆”：控制送入 AI 的新闻总长度
        filtered_articles = self.limit_input_articles(filtered_articles)

        # 3. 格式化为 Markdown
        print("\n📝 步骤 3: 格式化为 Markdown...")
        markdown_content = self.format_to_markdown(filtered_articles)

        # 抓取 & 整理完成后的内容长度监控
        content = markdown_content
        print(f"当前内容长度: {len(content)}")
        
        # 4. AI 分析
        print("\n🤖 步骤 4: AI 分析中...")
        analysis_result = self.analyze_with_ai(markdown_content)

        # AI 生成完成后的内容长度监控
        content = analysis_result
        print(f"当前内容长度: {len(content)}")
        
        # 5. 组合最终内容
        final_content = f"""## 📊 12小时金融资讯分析报告

{analysis_result}

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        # 推送前内容长度监控
        content = final_content
        print(f"当前内容长度: {len(content)}")
        
        # 6. 推送到飞书
        print("\n📤 步骤 5: 推送到飞书...")
        self.send_to_feishu(final_content)
        
        print("\n" + "=" * 50)
        print("✅ 任务完成！")
        print("=" * 50)


def main():
    """主函数"""
    agent = FinanceAgent()
    agent.run()


if __name__ == "__main__":
    main()
