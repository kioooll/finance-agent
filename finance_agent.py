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
            
            # 只保留内容长度 >= 15 字的文章
            if len(cleaned_content) >= 15:
                article['cleaned_content'] = cleaned_content
                filtered.append(article)
        
        return filtered
    
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
            
            # 构建请求体（兼容 OpenAI 格式）
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
                "max_tokens": 2000
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
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

[投资研判建议]：根据新闻逻辑，识别 1 个最可能的'主线题材'，推荐 2 只主板股或 ETF，并给出明确的买入理由及预计卖出条件。

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
            # 飞书 Webhook 支持 Markdown 格式
            payload = {
                "msg_type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "📊 金融资讯分析报告"
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": content
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
                print("✅ 飞书推送成功")
            else:
                print(f"❌ 飞书推送失败: {response.status_code} - {response.text}")
                
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
        
        # 3. 格式化为 Markdown
        print("\n📝 步骤 3: 格式化为 Markdown...")
        markdown_content = self.format_to_markdown(filtered_articles)
        
        # 4. AI 分析
        print("\n🤖 步骤 4: AI 分析中...")
        analysis_result = self.analyze_with_ai(markdown_content)
        
        # 5. 组合最终内容
        final_content = f"""## 📊 12小时金融资讯分析报告

{analysis_result}

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
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
