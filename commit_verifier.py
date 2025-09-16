#!/usr/bin/env python3
# =============================================================================
# GitHub功能提交跟踪验证脚本
# =============================================================================
# 使用说明：
# 1. 复制此脚本到项目根目录
# 2. 复制 config_template.yaml 并修改为项目实际配置
# 3. 配置 .env 文件填写 GitHub Token 和组织信息
# 4. 执行命令：python commit_verifier.py --config 你的配置文件.yaml
# =============================================================================
import sys
import os
import requests
import argparse
import yaml
import re
import base64
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# ==========================
# 1. 基础配置（通用无需修改）
# ==========================
# 默认文件路径（可通过命令行参数覆盖）
DEFAULT_ENV_FILE = ".env"  # 存储敏感信息（Token等）
DEFAULT_CONFIG_FILE = "config_template.yaml"  # 配置模板文件
GITHUB_API_VERSION = "application/vnd.github.v3+json"  # GitHub API 版本

# ==========================
# 2. 工具函数（通用无需修改）
# ==========================
def load_environment(env_path: str) -> Tuple[str, str]:
    """
    加载环境变量（从.env文件）
    返回：(GitHub Token, GitHub 组织名)
    """
    if not os.path.exists(env_path):
        print(f"❌ 错误：环境文件 {env_path} 不存在", file=sys.stderr)
        sys.exit(1)
    load_dotenv(env_path)
    github_token = os.getenv("GITHUB_TOKEN")  # 需在.env中定义
    github_org = os.getenv("GITHUB_ORG")      # 需在.env中定义
    if not github_token:
        print(f"❌ 错误：{env_path}文件中未配置 GITHUB_TOKEN", file=sys.stderr)
        sys.exit(1)
    if not github_org:
        print(f"❌ 错误：{env_path}文件中未配置 GITHUB_ORG", file=sys.stderr)
        sys.exit(1)
    return github_token, github_org

def load_project_config(config_path: str) -> Dict:
    """
    加载项目配置（从YAML文件）
    配置文件需包含：文档路径、验证规则、预期数据等
    """
    if not os.path.exists(config_path):
        print(f"❌ 错误：配置文件 {config_path} 不存在", file=sys.stderr)
        sys.exit(1)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 验证配置完整性（必须包含以下字段，缺一不可）
        required_config_fields = [
            "target_repo",          # 目标仓库名
            "target_branch",        # 目标分支
            "feature_doc_path",     # 特征文档路径
            "table_header",         # 特征表格表头
            "required_sections",    # 文档必填章节
            "min_feature_count",    # 最小特征数量
            "expected_features",    # 预期特征（{特征名: 预期SHA}）
            "expected_authors",     # 预期作者（{SHA: 作者名}）
            "expected_messages",    # 预期提交信息（{SHA: 信息}）
            "expected_dates"        # 预期日期（{SHA: 日期YYYY-MM-DD}）
        ]
        for field in required_config_fields:
            if field not in config:
                print(f"❌ 错误：配置文件缺少必填字段「{field}」", file=sys.stderr)
                sys.exit(1)
        
        return config
    except Exception as e:
        print(f"❌ 错误：加载配置文件失败 - {str(e)}", file=sys.stderr)
        sys.exit(1)

def get_github_headers(token: str) -> Dict[str, str]:
    """生成GitHub API请求头（通用无需修改）"""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": GITHUB_API_VERSION,
        "User-Agent": "GitHub-Commit-Verifier"
    }

def fetch_github_file(
    file_path: str,
    headers: Dict[str, str],
    org: str,
    repo: str,
    branch: str
) -> Optional[str]:
    """
    从GitHub仓库获取文件内容（自动解码Base64）
    返回：文件内容（字符串）或None（失败）
    """
    api_url = f"https://api.github.com/repos/{org}/{repo}/contents/{file_path}?ref={branch}"
    try:
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # GitHub API返回的文件内容是Base64编码
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8")
            return data.get("content", None)
        
        elif response.status_code == 404:
            print(f"❌ 错误：文件 {file_path} 在 {branch} 分支不存在", file=sys.stderr)
            return None
        
        else:
            print(f"❌ 错误：获取文件失败（状态码：{response.status_code}）- {response.text[:100]}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"❌ 错误：请求GitHub API异常 - {str(e)}", file=sys.stderr)
        return None

def verify_commit(
    commit_sha: str,
    headers: Dict[str, str],
    org: str,
    repo: str
) -> Optional[Dict]:
    """
    验证GitHub提交是否存在，并返回提交详情
    返回：提交详情（字典）或None（失败）
    """
    api_url = f"https://api.github.com/repos/{org}/{repo}/commits/{commit_sha}"
    try:
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        
        elif response.status_code == 404:
            print(f"❌ 错误：提交 {commit_sha[:8]} 不存在", file=sys.stderr)
            return None
        
        else:
            print(f"❌ 错误：验证提交失败（状态码：{response.status_code}）- {response.text[:100]}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"❌ 错误：请求提交详情异常 - {str(e)}", file=sys.stderr)
        return None

# ==========================
# 3. 核心逻辑（通用无需修改）
# ==========================
def parse_feature_table(content: str, table_header: str) -> List[Dict]:
    """
    解析Markdown文档中的特征表格
    表格格式要求：与配置文件中table_header一致
    返回：解析后的特征列表（每个元素是特征字典）
    """
    features = []
    lines = [line.strip() for line in content.split("\n")]
    in_table = False  # 是否进入表格区域
    for line in lines:
        # 1. 定位表格开始（找到配置的表头）
        if table_header in line:
            in_table = True
            continue
        
        # 2. 跳过表格分隔线（如：|----|----|----|）
        if in_table and line.startswith("|") and all(c in "-|" for c in line.replace("|", "")):
            continue
        
        # 3. 定位表格结束（遇到非表格行且包含章节标记）
        if in_table and line and not line.startswith("|") and "##" in line:
            break
        
        # 4. 解析表格行（格式：| 特征名 | SHA | 作者 | 分支 | 日期 | 改动文件 | 提交信息 |）
        if in_table and line.startswith("|"):
            # 分割表格列（去除首尾空字符）
            cols = [col.strip() for col in line.split("|") if col.strip()]
            # 确保列数与表头一致（表头示例：| Feature Name | Commit SHA | ... | 共7列）
            if len(cols) >= 7:
                feature = {
                    "name": cols[0],          # 特征名
                    "sha": cols[1],           # 提交SHA
                    "author": cols[2],        # 作者
                    "branch": cols[3],        # 分支
                    "date": cols[4],          # 日期
                    "files_changed": cols[5], # 改动文件数
                    "message": cols[6]        # 提交信息
                }
                features.append(feature)
    
    return features

def run_verification(config: Dict, github_token: str, github_org: str) -> bool:
    """
    执行完整验证流程
    返回：True（验证通过）/ False（验证失败）
    """
    # 初始化GitHub请求头
    headers = get_github_headers(github_token)
    # 提取配置参数（简化后续调用）
    repo = config["target_repo"]
    branch = config["target_branch"]
    doc_path = config["feature_doc_path"]
    table_header = config["table_header"]
    required_sections = config["required_sections"]
    min_feat_count = config["min_feature_count"]
    expected_feats = config["expected_features"]
    expected_authors = config["expected_authors"]
    expected_msgs = config["expected_messages"]
    expected_dates = config["expected_dates"]
    print("=" * 60)
    print(f"📋 开始验证：{github_org}/{repo}@{branch}")
    print(f"📄 目标文档：{doc_path}")
    print("=" * 60)

    # --------------------------
    # 步骤1：获取特征文档内容
    # --------------------------
    print("\n1. 📥 获取特征文档...")
    doc_content = fetch_github_file(doc_path, headers, github_org, repo, branch)
    if not doc_content:
        return False
    print(f"✅ 成功获取文档（大小：{len(doc_content)} 字符）")

    # --------------------------
    # 步骤2：验证文档必填章节
    # --------------------------
    print(f"\n2. 📝 验证文档章节...")
    for section in required_sections:
        if section not in doc_content:
            print(f"❌ 缺失必填章节：「{section}」", file=sys.stderr)
            return False
    print(f"✅ 所有 {len(required_sections)} 个必填章节均存在")

    # --------------------------
    # 步骤3：解析特征表格
    # --------------------------
    print(f"\n3. 🔍 解析特征表格...")
    features = parse_feature_table(doc_content, table_header)
    if len(features) == 0:
        print("❌ 未解析到任何特征（表格格式可能错误）", file=sys.stderr)
        return False
    print(f"✅ 解析到 {len(features)} 个特征")

    # --------------------------
    # 步骤4：验证特征数量
    # --------------------------
    print(f"\n4. 📊 验证特征数量...")
    if len(features) < min_feat_count:
        print(f"❌ 特征数量不足（预期≥{min_feat_count}，实际={len(features)}）", file=sys.stderr)
        return False
    print(f"✅ 特征数量满足要求（{len(features)} ≥ {min_feat_count}）")

    # --------------------------
    # 步骤5：验证预期特征与SHA
    # --------------------------
    print(f"\n5. 🔗 验证特征与SHA匹配...")
    feat_name_to_sha = {feat["name"]: feat["sha"] for feat in features}
    for expected_name, expected_sha in expected_feats.items():
        # 检查特征是否存在
        if expected_name not in feat_name_to_sha:
            print(f"❌ 预期特征「{expected_name}」未在表格中找到", file=sys.stderr)
            return False
        # 检查SHA是否匹配
        actual_sha = feat_name_to_sha[expected_name]
        if actual_sha != expected_sha:
            print(f"❌ 特征「{expected_name}」SHA不匹配：")
            print(f"   预期：{expected_sha[:8]}...")
            print(f"   实际：{actual_sha[:8]}...", file=sys.stderr)
            return False
    print(f"✅ 所有 {len(expected_feats)} 个预期特征SHA均匹配")

    # --------------------------
    # 步骤6：验证提交详情（作者、信息、日期）
    # --------------------------
    print(f"\n6. 📅 验证提交详情...")
    for feat in features:
        feat_sha = feat["sha"]
        # 仅验证配置中指定的预期提交
        if feat_sha not in expected_authors:
            continue
        
        # 验证提交是否存在
        commit_detail = verify_commit(feat_sha, headers, github_org, repo)
        if not commit_detail:
            return False
        
        # 验证作者
        expected_author = expected_authors[feat_sha]
        actual_author = commit_detail.get("author", {}).get("login", "")
        if actual_author != expected_author:
            print(f"❌ 提交 {feat_sha[:8]} 作者不匹配：")
            print(f"   预期：{expected_author}")
            print(f"   实际：{actual_author}", file=sys.stderr)
            return False
        
        # 验证提交信息（表格中的信息 vs 实际提交信息）
        expected_msg = expected_msgs[feat_sha]
        # 表格中的信息
        if feat["message"] != expected_msg:
            print(f"❌ 提交 {feat_sha[:8]} 表格信息不匹配：")
            print(f"   预期：{expected_msg}")
            print(f"   实际：{feat['message']}", file=sys.stderr)
            return False
        # GitHub实际提交信息（取第一行）
        actual_commit_msg = commit_detail.get("commit", {}).get("message", "").split("\n")[0]
        if actual_commit_msg != expected_msg:
            print(f"❌ 提交 {feat_sha[:8]} GitHub信息不匹配：")
            print(f"   预期：{expected_msg}")
            print(f"   实际：{actual_commit_msg}", file=sys.stderr)
            return False
        
        # 验证日期（格式+内容）
        expected_date = expected_dates[feat_sha]
        # 检查日期格式（YYYY-MM-DD）
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", feat["date"]):
            print(f"❌ 特征「{feat['name']}」日期格式错误（应为YYYY-MM-DD）：{feat['date']}", file=sys.stderr)
            return False
        # 检查日期内容
        if feat["date"] != expected_date:
            print(f"❌ 提交 {feat_sha[:8]} 日期不匹配：")
            print(f"   预期：{expected_date}")
            print(f"   实际：{feat['date']}", file=sys.stderr)
            return False
    print(f"✅ 所有 {len(expected_authors)} 个提交详情均验证通过")

    # --------------------------
    # 步骤7：验证表格格式标准化
    # --------------------------
    print(f"\n7. 📋 验证表格格式标准化...")
    for feat in features:
        # 检查关键字段是否为空
        if not feat["name"] or not feat["sha"] or not feat["author"]:
            print(f"❌ 特征表格行存在空关键字段：{feat}", file=sys.stderr)
            return False
    print(f"✅ 表格格式标准化验证通过")

    # --------------------------
    # 验证完成
    # --------------------------
    print("\n" + "=" * 60)
    print("🎉 所有验证步骤均通过！")
    print(f"📊 验证总结：")
    print(f"   - 目标组织：{github_org}")
    print(f"   - 目标仓库：{repo}")
    print(f"   - 目标分支：{branch}")
    print(f"   - 特性文档路径：{doc_path}")
    print(f"   - 跟踪的特性数量：{len(features)}")
    print(f"   - 验证的预期特性数量：{len(expected_feats)}")
    print(f"   - 通过的检查项目：7项（文档存在性、章节完整性、表格解析、特性数量、SHA一致性、提交详情、表格格式）")
    print("=" * 60)
    return True

# ==========================
# 4. 入口函数（通用无需修改）
# ==========================
def main():
    # 解析命令行参数（支持指定配置文件和.env文件路径）
    parser = argparse.ArgumentParser(description="GitHub功能提交跟踪验证脚本")
    parser.add_argument(
        "--config",
        type=str,
        default=DEFAULT_CONFIG_FILE,
        help=f"配置文件路径（默认：{DEFAULT_CONFIG_FILE}）"
    )
    parser.add_argument(
        "--env",
        type=str,
        default=DEFAULT_ENV_FILE,
        help=f"环境文件路径（默认：{DEFAULT_ENV_FILE}）"
    )
    args = parser.parse_args()
    # 1. 加载环境变量（Token、组织名）
    print(f"📌 加载环境变量：{args.env}")
    github_token, github_org = load_environment(args.env)
    # 2. 加载项目配置（仓库、分支、文档路径等）
    print(f"📌 加载项目配置：{args.config}")
    project_config = load_project_config(args.config)
    # 3. 执行核心验证逻辑
    print("\n" + "-" * 50)
    verification_result = run_verification(project_config, github_token, github_org)
    # 4. 根据验证结果退出程序（0=成功，1=失败）
    sys.exit(0 if verification_result else 1)

# 脚本入口（当直接执行脚本时触发）
if __name__ == "__main__":
    main()