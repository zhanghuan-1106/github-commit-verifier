# GitHub 功能提交跟踪验证工具

一个用于验证 GitHub 仓库功能提交跟踪工作流的自动化工具，确保特性开发过程可追溯、有文档记录，并与预定义规则保持一致。

## 功能特性

- 自动验证特性文档的存在性和完整性
- 解析并验证特性提交表格的数据有效性
- 检查提交 SHA 的一致性和存在性
- 验证提交详细信息（作者、消息、日期）的合规性
- 确保表格格式标准化
- 提供详细的验证日志和最终总结报告

## 安装要求

- Python 3.6+
- 必需的 Python 库：
  ```bash
  pip install requests python-dotenv pyyaml
  ```

## 快速开始

### 1. 克隆或下载脚本

```bash
# 克隆仓库（如果适用）
git clone https://github.com/您的用户名/您的仓库名.git
cd 您的仓库名
```

### 2. 配置环境变量

创建 `.env` 文件并添加以下内容：

```
GITHUB_TOKEN=您的GitHub个人访问令牌
GITHUB_ORG=您的GitHub用户名或组织名
```

> **注意**：GitHub 令牌需要具有 `repo` 权限才能访问仓库内容和提交数据。

### 3. 配置项目设置

创建或修改 `config_template.yaml` 文件，根据您的项目需求配置验证规则：

```yaml
# 目标仓库配置
target_repo: "您的仓库名称"
target_branch: "main"

# 特性文档配置
feature_doc_path: "FEATURE_COMMITS.md"
table_header: "| Feature Name | Commit SHA | Author | Branch | Date | Files Changed | Message |"

# 文档必填章节
required_sections:
  - "# Feature Development Tracking"
  - "## Feature Commit History"

# 特征数量要求
min_feature_count: 3

# 预期特性与SHA映射
expected_features:
  "User Authentication": "实际存在的SHA1值"
  "Payment Gateway": "实际存在的SHA2值"
  "Dashboard Redesign": "实际存在的SHA3值"

# 预期作者与SHA映射
expected_authors:
  "实际存在的SHA1值": "johndoe"
  "实际存在的SHA2值": "janedoe"
  "实际存在的SHA3值": "bobsmith"

# 预期提交信息与SHA映射
expected_messages:
  "实际存在的SHA1值": "Implement user authentication system"
  "实际存在的SHA2值": "Add payment gateway integration"
  "实际存在的SHA3值": "Redesign user dashboard interface"

# 预期提交日期与SHA映射
expected_dates:
  "实际存在的SHA1值": "2023-05-15"
  "实际存在的SHA2值": "2023-06-20"
  "实际存在的SHA3值": "2023-07-10"
```

### 4. 创建或更新特性跟踪文档

确保您的仓库中存在 `FEATURE_COMMITS.md` 文件，并按照以下格式记录功能提交：

```markdown
# Feature Development Tracking

This document tracks all feature development commits in the project.

## Feature Commit History

| Feature Name | Commit SHA | Author | Branch | Date | Files Changed | Message |
|--------------|------------|--------|--------|------|---------------|---------|
| User Authentication | 实际存在的SHA1值 | johndoe | feature/auth | 2023-05-15 | 12 | Implement user authentication system |
| Payment Gateway | 实际存在的SHA2值 | janedoe | feature/payment | 2023-06-20 | 8 | Add payment gateway integration |
| Dashboard Redesign | 实际存在的SHA3值 | bobsmith | feature/ui-redesign | 2023-07-10 | 15 | Redesign user dashboard interface |

## Feature Approval Process

All features must follow the approval process outlined in our development guidelines.

## Future Features

- Mobile app development
- Multi-language support
- Advanced reporting system
```

### 5. 运行验证脚本

```bash
python commit_verifier.py --config config_template.yaml --env .env
```

## 验证流程

脚本执行以下验证步骤：

1. **环境配置验证**：检查 GitHub 令牌和组织名是否正确配置
2. **项目配置验证**：确保配置文件包含所有必需字段
3. **特性文档存在性验证**：检查特性跟踪文档是否存在
4. **文档章节完整性验证**：确认文档包含所有必需章节
5. **特性表格解析验证**：解析表格并验证特征数量
6. **特性-SHA一致性验证**：检查预期特征的 SHA 是否匹配
7. **提交存在性验证**：通过 GitHub API 验证提交是否存在
8. **提交详细信息验证**：验证作者、提交信息和日期
9. **表格格式标准化验证**：确保表格行包含完整信息

## 输出结果

### 成功验证

当所有验证步骤通过时，脚本将输出类似以下内容：

```
============================================================
📋 开始验证：您的用户名/您的仓库名@main
📄 目标文档：FEATURE_COMMITS.md
============================================================

1. 📥 获取特征文档...
✅ 成功获取文档（大小：1024 字符）

2. 📝 验证文档章节...
✅ 所有 2 个必填章节均存在

3. 🔍 解析特征表格...
✅ 解析到 4 个特征

4. 📊 验证特征数量...
✅ 特征数量满足要求（4 ≥ 3）

5. 🔗 验证特征与SHA匹配...
✅ 所有 3 个预期特征SHA均匹配

6. 📅 验证提交详情...
✅ 所有 3 个提交详情均验证通过

7. 📋 验证表格格式标准化...
✅ 表格格式标准化验证通过

============================================================
🎉 所有验证步骤均通过！
📊 验证总结：
   - 目标组织：您的用户名
   - 目标仓库：您的仓库名
   - 目标分支：main
   - 特性文档路径：FEATURE_COMMITS.md
   - 跟踪的特性数量：4
   - 验证的预期特性数量：3
   - 通过的检查项目：7项（文档存在性、章节完整性、表格解析、特性数量、SHA一致性、提交详情、表格格式）
============================================================
```

### 验证失败

如果任何验证步骤失败，脚本将输出相应的错误信息，并以状态码 1 退出。

## 故障排除

### 常见问题

1. **"No commit found for SHA" 错误**
   - 确保 YAML 配置文件和 Markdown 文档中的 SHA 值是实际存在于仓库中的提交
   - 检查 SHA 值是否完整（40位）且准确无误

2. **"环境文件不存在" 错误**
   - 确保 `.env` 文件存在于脚本所在目录
   - 检查文件名是否正确（包括前导点）

3. **"配置文件缺少必填字段" 错误**
   - 检查 YAML 配置文件是否包含所有必需字段
   - 确保 YAML 格式正确，没有缩进错误

4. **"获取文件失败" 错误**
   - 检查 GitHub 令牌是否有效且具有 `repo` 权限
   - 确认仓库和组织名称正确

### 获取帮助

如果遇到其他问题，请检查：

1. GitHub 令牌权限是否足够
2. 网络连接是否正常
3. 仓库是否为公开仓库或令牌是否有权限访问私有仓库
4. 配置文件中的路径和分支名称是否正确


## 贡献

欢迎提交问题报告和改进建议！
