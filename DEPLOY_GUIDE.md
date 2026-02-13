# 📚 金融资讯自动化分析系统 - 部署指南

本指南将详细讲解如何将这个金融资讯自动化分析系统部署到 GitHub，并配置自动运行。

---

## 📋 目录

1. [准备工作](#准备工作)
2. [创建 GitHub 仓库](#创建-github-仓库)
3. [配置 Secrets（密钥）](#配置-secrets密钥)
4. [上传文件到 GitHub](#上传文件到-github)
5. [验证运行](#验证运行)
6. [常见问题](#常见问题)

---

## 🛠️ 准备工作

在开始之前，你需要准备以下信息：

1. **AI API 配置**（三选一或使用中转 API）：
   - `AI_MODEL`: 模型名称（如 `gpt-4`、`gpt-3.5-turbo`、`claude-3-opus` 等）
   - `AI_BASE_URL`: API 基础地址（如 `https://api.openai.com` 或你的中转地址）
   - `AI_API_KEY`: API 密钥

2. **飞书 Webhook 地址**：
   - `FEISHU_WEBHOOK`: 飞书群聊机器人的 Webhook URL

---

## 📦 创建 GitHub 仓库

### 步骤 1: 登录 GitHub

访问 [GitHub.com](https://github.com) 并登录你的账号。

### 步骤 2: 创建新仓库

1. 点击右上角的 **"+"** 按钮，选择 **"New repository"**
2. 填写仓库信息：
   - **Repository name**: 例如 `finance-agent`（可以自定义）
   - **Description**: 可选，例如 "金融资讯自动化分析系统"
   - **Visibility**: 选择 **Private**（私有）或 **Public**（公开）
   - **不要**勾选 "Initialize this repository with a README"（因为我们已经有文件了）
3. 点击 **"Create repository"** 创建仓库

---

## 🔐 配置 Secrets（密钥）

这一步非常重要！我们需要在 GitHub 仓库中设置密钥，这样脚本才能访问你的 API 和飞书 Webhook。

### 步骤 1: 进入仓库设置

1. 在你的 GitHub 仓库页面，点击顶部的 **"Settings"**（设置）标签
2. 在左侧菜单中找到 **"Secrets and variables"** → **"Actions"**
3. 点击 **"New repository secret"** 按钮

### 步骤 2: 添加四个 Secrets

你需要添加以下四个密钥（每个都要单独添加）：

#### 1️⃣ AI_MODEL（AI 模型名称）

- **Name**: `AI_MODEL`
- **Secret**: 输入你的模型名称，例如：
  - `gpt-4`
  - `gpt-3.5-turbo`
  - `claude-3-opus`
  - 或其他你使用的模型名称
- 点击 **"Add secret"**

#### 2️⃣ AI_BASE_URL（AI API 基础地址）

- **Name**: `AI_BASE_URL`
- **Secret**: 输入你的 API 基础地址，例如：
  - OpenAI 官方: `https://api.openai.com`
  - 中转 API: `https://your-proxy.com`（替换为你的中转地址）
- 点击 **"Add secret"**

#### 3️⃣ AI_API_KEY（AI API 密钥）

- **Name**: `AI_API_KEY`
- **Secret**: 输入你的 API 密钥（通常是一串以 `sk-` 开头的字符串）
- ⚠️ **注意**: 这个密钥非常重要，不要泄露给任何人！
- 点击 **"Add secret"**

#### 4️⃣ FEISHU_WEBHOOK（飞书 Webhook 地址）

- **Name**: `FEISHU_WEBHOOK`
- **Secret**: 输入你的飞书群聊机器人 Webhook URL，格式类似：
  - `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxxxxx`
- 点击 **"Add secret"**

### ✅ 验证 Secrets 已添加

添加完成后，你应该在 Secrets 列表中看到这四个密钥：
- `AI_MODEL`
- `AI_BASE_URL`
- `AI_API_KEY`
- `FEISHU_WEBHOOK`

---

## 📤 上传文件到 GitHub

有几种方法可以上传文件，这里介绍最简单的方法：

### 方法一：使用 GitHub 网页界面（推荐新手）

#### 步骤 1: 进入仓库

1. 打开你的 GitHub 仓库页面
2. 确保你在 **"Code"**（代码）标签页

#### 步骤 2: 上传文件

1. 点击 **"Add file"** → **"Upload files"**
2. 将以下文件拖拽到上传区域，或点击选择文件：
   - `finance_agent.py`
   - `requirements.txt`
   - `.github/workflows/main.yml`
   - `DEPLOY_GUIDE.md`（可选，但建议上传）
3. 在页面底部填写提交信息（Commit message），例如：
   - `Initial commit: Add finance agent script`
4. 点击 **"Commit changes"**（提交更改）

### 方法二：使用 Git 命令行（适合有 Git 经验的用户）

如果你本地已经安装了 Git，可以使用命令行：

```bash
# 1. 初始化 Git 仓库（如果还没有）
git init

# 2. 添加所有文件
git add .

# 3. 提交
git commit -m "Initial commit: Add finance agent script"

# 4. 添加远程仓库（替换 YOUR_USERNAME 和 YOUR_REPO_NAME）
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 5. 推送到 GitHub
git branch -M main
git push -u origin main
```

### 方法三：使用 GitHub Desktop（图形化工具）

1. 下载并安装 [GitHub Desktop](https://desktop.github.com/)
2. 登录你的 GitHub 账号
3. 点击 **"File"** → **"Add Local Repository"**
4. 选择包含这些文件的文件夹
5. 点击 **"Publish repository"** 推送到 GitHub

---

## ✅ 验证运行

### 步骤 1: 手动触发一次运行

1. 进入你的 GitHub 仓库页面
2. 点击顶部的 **"Actions"**（操作）标签
3. 在左侧找到 **"Finance Agent Daily Run"** 工作流
4. 点击右侧的 **"Run workflow"** 按钮
5. 选择分支（通常是 `main` 或 `master`）
6. 点击绿色的 **"Run workflow"** 按钮

### 步骤 2: 查看运行日志

1. 点击刚创建的运行任务（会显示 "Queued" 或 "In progress"）
2. 点击左侧的 **"finance-analysis"** 任务
3. 展开各个步骤查看详细日志：
   - ✅ **检出代码**: 应该成功
   - ✅ **设置 Python 环境**: 应该成功
   - ✅ **安装依赖**: 应该成功
   - ✅ **运行金融分析脚本**: 查看是否有错误

### 步骤 3: 检查飞书推送

如果一切正常，你应该在配置的飞书群聊中收到一条消息，包含：
- 📊 12小时金融资讯分析报告
- [12小时要闻总结]
- [投资研判建议]

### 🎉 成功标志

如果看到以下情况，说明部署成功：
- ✅ Actions 页面显示绿色的 ✓ 标记
- ✅ 飞书群聊收到分析报告
- ✅ 日志中没有错误信息

---

## ⏰ 自动运行时间

脚本配置为每天自动运行两次：
- **北京时间 08:15**（UTC 00:15）
- **北京时间 20:15**（UTC 12:15）

你可以在 **Actions** 标签页查看历史运行记录。

---

## ❓ 常见问题

### Q1: Secrets 在哪里找到？

**A**: 在仓库页面 → **Settings** → **Secrets and variables** → **Actions**

### Q2: 如何修改运行时间？

**A**: 编辑 `.github/workflows/main.yml` 文件，修改 `cron` 表达式：
- 格式: `分钟 小时 * * *`（UTC 时区）
- 北京时间 08:15 = UTC 00:15 → `'15 0 * * *'`
- 北京时间 20:15 = UTC 12:15 → `'15 12 * * *'`

### Q3: 如何获取飞书 Webhook？

**A**: 
1. 打开飞书，进入目标群聊
2. 点击群设置 → **群机器人** → **添加机器人** → **自定义机器人**
3. 填写机器人名称和描述
4. 复制生成的 **Webhook 地址**

### Q4: 脚本运行失败怎么办？

**A**: 
1. 检查 **Actions** 页面的日志，找到错误信息
2. 常见问题：
   - Secrets 未正确配置 → 检查 Secrets 是否都已添加
   - API 密钥错误 → 检查 `AI_API_KEY` 是否正确
   - 网络问题 → RSS 源可能暂时不可用
   - 依赖安装失败 → 检查 `requirements.txt` 是否正确

### Q5: 如何本地测试脚本？

**A**: 
1. 安装依赖: `pip install -r requirements.txt`
2. 设置环境变量（Windows PowerShell）:
   ```powershell
   $env:AI_MODEL="gpt-4"
   $env:AI_BASE_URL="https://api.openai.com"
   $env:AI_API_KEY="your-api-key"
   $env:FEISHU_WEBHOOK="your-webhook-url"
   ```
3. 运行脚本: `python finance_agent.py`

### Q6: 可以添加更多 RSS 源吗？

**A**: 可以！编辑 `finance_agent.py` 文件，在 `self.rss_sources` 列表中添加新的源：
```python
{"name": "新源名称", "url": "RSS地址"},
```

### Q7: GitHub Actions 有运行次数限制吗？

**A**: 
- 免费账户：私有仓库每月 2000 分钟，公开仓库无限
- 每天运行 2 次，每次约 1-2 分钟，完全够用

---

## 📞 需要帮助？

如果遇到问题：
1. 检查 GitHub Actions 日志
2. 确认所有 Secrets 都已正确配置
3. 验证飞书 Webhook 是否有效
4. 检查 AI API 是否可用

---

**祝部署顺利！🎉**
