#!/usr/bin/env python3
"""
本地 HTTP 服务器，用于浏览学习路径和查看 Markdown 文件
"""
import os
import yaml
import markdown
from flask import Flask, render_template_string, send_from_directory, abort
from pathlib import Path

app = Flask(__name__)

# 项目根目录
BASE_DIR = Path(__file__).parent


def load_config():
    """从 CONFIG 文件加载配置"""
    config = {}
    config_file = BASE_DIR / "CONFIG"

    if not config_file.exists():
        raise FileNotFoundError(f"CONFIG file not found at {config_file}")

    with open(config_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释行
            if not line or line.startswith('#'):
                continue
            # 解析 key: value 格式
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                # 移除引号（如果有）
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                config[key] = value

    return config


# 加载配置
CONFIG = load_config()

# 从 CONFIG 读取路径
YAML_FILE = BASE_DIR / CONFIG.get('LEARNING_GOAL', 'input/this_is_what_I_want_to_learn.yaml')
OUTPUT_DIR = BASE_DIR / CONFIG.get('GENERATED_LEARNING_MATERIAL_FOLDER', 'output')

# 主页 HTML 模板
HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            /* Dark theme (default) */
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --bg-hover: #30363d;
            --bg-code: #161b22;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --text-title: #f0f6fc;
            --border-color: #30363d;
            --link-color: #58a6ff;
            --link-hover: #79c0ff;
            --shadow: rgba(0,0,0,0.3);
        }

        [data-theme="light"] {
            /* Light theme */
            --bg-primary: #ffffff;
            --bg-secondary: #f6f8fa;
            --bg-tertiary: #ffffff;
            --bg-hover: #f3f4f6;
            --text-primary: #24292f;
            --text-secondary: #57606a;
            --text-title: #1f2328;
            --border-color: #d0d7de;
            --link-color: #0969da;
            --link-hover: #0860ca;
            --shadow: rgba(0,0,0,0.1);
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: var(--bg-primary);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.7;
            color: var(--text-primary);
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: var(--bg-secondary);
            border-radius: 8px;
            box-shadow: 0 4px 12px var(--shadow);
            overflow: hidden;
            border: 1px solid var(--border-color);
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }

        .header {
            background: var(--bg-secondary);
            color: var(--text-primary);
            padding: 90px 30px 40px 30px;
            text-align: center;
            border-bottom: 2px solid var(--border-color);
            position: relative;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }

        .header-actions {
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .theme-toggle {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 12px;
            cursor: pointer;
            color: var(--text-primary);
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
            white-space: nowrap;
        }

        .theme-toggle:hover {
            background: var(--bg-hover);
            border-color: var(--link-color);
        }

        .theme-toggle svg {
            width: 16px;
            height: 16px;
            fill: currentColor;
        }

        .progress-info {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
            color: var(--text-primary);
            font-weight: 600;
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-width: 140px;
            max-width: 160px;
        }

        .progress-info .progress-number {
            color: var(--link-color);
        }

        .progress-info > div:first-child {
            display: flex;
            justify-content: space-between;
            align-items: center;
            white-space: nowrap;
        }

        .progress-bar-container {
            width: 100%;
            height: 6px;
            background: var(--bg-secondary);
            border-radius: 3px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--link-color), var(--link-hover));
            border-radius: 3px;
            transition: width 0.3s ease;
            min-width: 2px;
        }

        [data-theme="dark"] .progress-bar-fill {
            background: linear-gradient(90deg, #238636, #2ea043);
        }

        [data-theme="light"] .progress-bar-fill {
            background: linear-gradient(90deg, #2da44e, #2c974b);
        }

        .header h1 {
            font-size: 2.2em;
            margin-bottom: 15px;
            font-weight: 700;
            color: var(--text-title);
            transition: color 0.3s ease;
        }

        .header p {
            font-size: 1.15em;
            font-weight: 400;
            color: var(--text-secondary);
            transition: color 0.3s ease;
        }

        .content {
            padding: 40px;
            background: var(--bg-secondary);
            transition: background-color 0.3s ease;
        }

        .module-section {
            margin-bottom: 50px;
        }

        .section-title {
            font-size: 1.6em;
            color: var(--text-title);
            margin-bottom: 25px;
            padding: 18px 20px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            border-left: 4px solid var(--link-color);
            font-weight: 700;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        .module-list {
            list-style: none;
            display: grid;
            gap: 15px;
        }

        .module-item {
            padding: 20px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            border-left: 4px solid var(--link-color);
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px var(--shadow);
            border: 1px solid var(--border-color);
            position: relative;
        }

        .module-item.completed {
            border-left-color: #2da44e;
            opacity: 0.85;
        }

        [data-theme="dark"] .module-item.completed {
            border-left-color: #3fb950;
        }

        .module-item:hover {
            background: var(--bg-hover);
            transform: translateX(4px);
            box-shadow: 0 4px 8px var(--shadow);
            border-left-color: var(--link-hover);
            border-color: var(--link-color);
            opacity: 1;
        }

        .module-link {
            text-decoration: none;
            color: var(--text-primary);
            display: block;
            transition: color 0.3s ease;
        }

        .module-link:hover {
            color: var(--link-color);
        }

        .module-checkbox {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 24px;
            height: 24px;
            cursor: pointer;
            appearance: none;
            border: 2px solid var(--border-color);
            border-radius: 4px;
            background: var(--bg-tertiary);
            transition: all 0.2s ease;
        }

        .module-checkbox:checked {
            background: #2da44e;
            border-color: #2da44e;
        }

        [data-theme="dark"] .module-checkbox:checked {
            background: #3fb950;
            border-color: #3fb950;
        }

        .module-checkbox:checked::after {
            content: '✓';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 16px;
            font-weight: bold;
        }

        .module-checkbox:hover {
            border-color: var(--link-color);
        }

        .module-id {
            font-weight: 700;
            color: var(--link-color);
            margin-right: 12px;
            font-size: 1.05em;
            font-family: 'Monaco', 'Menlo', monospace;
            transition: color 0.3s ease;
        }

        .module-title {
            font-size: 1.15em;
            margin-bottom: 8px;
            font-weight: 600;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            color: var(--text-title);
            transition: color 0.3s ease;
            padding-right: 40px;
        }

        .module-description {
            color: var(--text-secondary);
            font-size: 0.95em;
            margin-top: 10px;
            line-height: 1.7;
            transition: color 0.3s ease;
        }

        .module-type {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 0.75em;
            margin-left: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: 1px solid currentColor;
        }

        [data-theme="dark"] .type-concept {
            background: #1c2128;
            color: #79c0ff;
            border-color: #79c0ff;
        }

        [data-theme="light"] .type-concept {
            background: #ddf4ff;
            color: #0969da;
            border-color: #0969da;
        }

        [data-theme="dark"] .type-mechanism {
            background: #1c2128;
            color: #d2a8ff;
            border-color: #d2a8ff;
        }

        [data-theme="light"] .type-mechanism {
            background: #fbefff;
            color: #8250df;
            border-color: #8250df;
        }

        [data-theme="dark"] .type-practice {
            background: #1c2128;
            color: #7ee787;
            border-color: #7ee787;
        }

        [data-theme="light"] .type-practice {
            background: #dafbe1;
            color: #1a7f37;
            border-color: #1a7f37;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-actions">
                <div class="progress-info">
                    <div>
                        <span>进度:</span>
                        <span class="progress-number" id="progressText">0/0</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" id="progressBar" style="width: 0%;"></div>
                    </div>
                </div>
                <button class="theme-toggle" id="themeToggle" aria-label="切换主题">
                    <svg id="themeIcon" viewBox="0 0 16 16" width="16" height="16">
                        <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM2 8a6 6 0 0 1 6-6v12a6 6 0 0 1-6-6Z"></path>
                    </svg>
                    <span id="themeText">浅色</span>
                </button>
            </div>
            <h1>{{ title }}</h1>
            <p>{{ description }}</p>
        </div>
        <div class="content">
            {% for section in sections %}
            <div class="module-section">
                <h2 class="section-title">{{ section.title }}</h2>
                <ul class="module-list">
                    {% for module in section.modules %}
                    <li class="module-item" data-module-id="{{ module.id }}">
                        <input type="checkbox" class="module-checkbox" id="check-{{ module.id }}" data-module-id="{{ module.id }}">
                        <a href="/view/{{ module.id }}" class="module-link">
                            <div class="module-title">
                                <span class="module-id">{{ module.id }}</span>
                                {{ module.title }}
                                <span class="module-type type-{{ module.type }}">{{ module.type }}</span>
                            </div>
                            <div class="module-description">{{ module.description }}</div>
                        </a>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            {% endfor %}
        </div>
    </div>
    <script>
        (function() {
            const themeToggle = document.getElementById('themeToggle');
            const themeIcon = document.getElementById('themeIcon');
            const themeText = document.getElementById('themeText');
            const html = document.documentElement;
            const progressText = document.getElementById('progressText');

            // 从 localStorage 读取主题偏好，默认为 dark
            const currentTheme = localStorage.getItem('theme') || 'dark';
            html.setAttribute('data-theme', currentTheme);
            updateThemeIcon(currentTheme);

            themeToggle.addEventListener('click', function() {
                const current = html.getAttribute('data-theme');
                const newTheme = current === 'dark' ? 'light' : 'dark';
                html.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
                updateThemeIcon(newTheme);
            });

            function updateThemeIcon(theme) {
                if (theme === 'dark') {
                    themeIcon.innerHTML = '<path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM2 8a6 6 0 0 1 6-6v12a6 6 0 0 1-6-6Z"></path>';
                    themeText.textContent = '浅色';
                } else {
                    themeIcon.innerHTML = '<path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0-1.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5ZM8 0a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0V.75A.75.75 0 0 1 8 0ZM8 13.5a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 8 13.5ZM2.343 2.343a.75.75 0 0 1 1.061 0l1.06 1.061a.75.75 0 0 1-1.06 1.06l-1.061-1.06a.75.75 0 0 1 0-1.061Zm9.193 9.193a.75.75 0 0 1 1.06 0l1.061 1.06a.75.75 0 0 1-1.06 1.061l-1.061-1.06a.75.75 0 0 1 0-1.061ZM0 8a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5H.75A.75.75 0 0 1 0 8Zm13.5 0a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5h-1.5A.75.75 0 0 1 13.5 8ZM2.343 13.657a.75.75 0 0 1 0-1.061l1.061-1.06a.75.75 0 0 1 1.06 1.06l-1.06 1.061a.75.75 0 0 1-1.061 0Zm9.193-9.193a.75.75 0 0 1 0-1.06l1.06-1.061a.75.75 0 1 1 1.061 1.06l-1.061 1.061a.75.75 0 0 1-1.06 0Z"></path>';
                    themeText.textContent = '深色';
                }
            }

            // 学习进度管理
            function getProgress() {
                const progress = localStorage.getItem('learningProgress');
                return progress ? JSON.parse(progress) : {};
            }

            function saveProgress(progress) {
                localStorage.setItem('learningProgress', JSON.stringify(progress));
            }

            function updateProgress() {
                const progress = getProgress();
                const checkboxes = document.querySelectorAll('.module-checkbox');
                let completed = 0;
                let total = checkboxes.length;

                // 存储模块总数到 localStorage，供其他页面使用
                localStorage.setItem('totalModules', total.toString());

                checkboxes.forEach(checkbox => {
                    const moduleId = checkbox.dataset.moduleId;
                    const isCompleted = progress[moduleId] === true;
                    checkbox.checked = isCompleted;

                    const moduleItem = checkbox.closest('.module-item');
                    if (isCompleted) {
                        moduleItem.classList.add('completed');
                        completed++;
                    } else {
                        moduleItem.classList.remove('completed');
                    }
                });

                progressText.textContent = completed + '/' + total;

                // 更新进度条
                const progressBar = document.getElementById('progressBar');
                if (progressBar && total > 0) {
                    const percentage = (completed / total) * 100;
                    progressBar.style.width = percentage + '%';
                }
            }

            // 初始化进度
            updateProgress();

            // 监听复选框变化
            document.querySelectorAll('.module-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', function(e) {
                    e.stopPropagation(); // 阻止事件冒泡到链接
                    const moduleId = this.dataset.moduleId;
                    const progress = getProgress();
                    progress[moduleId] = this.checked;
                    saveProgress(progress);
                    updateProgress();
                });
            });
        })();
    </script>
</body>
</html>
"""

# Markdown 查看页面模板
MARKDOWN_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            /* Dark theme (default) */
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --bg-hover: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --text-title: #f0f6fc;
            --border-color: #30363d;
            --link-color: #58a6ff;
            --link-hover: #79c0ff;
            --shadow: rgba(0,0,0,0.3);
            --button-bg: #238636;
            --button-hover: #2ea043;
        }

        [data-theme="light"] {
            /* Light theme */
            --bg-primary: #ffffff;
            --bg-secondary: #f6f8fa;
            --bg-tertiary: #ffffff;
            --bg-hover: #f3f4f6;
            --bg-code: #f6f8fa;
            --text-primary: #24292f;
            --text-secondary: #57606a;
            --text-title: #1f2328;
            --border-color: #d0d7de;
            --link-color: #0969da;
            --link-hover: #0860ca;
            --shadow: rgba(0,0,0,0.1);
            --button-bg: #2da44e;
            --button-hover: #2c974b;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: var(--bg-primary);
            padding: 20px;
            line-height: 1.7;
            color: var(--text-primary);
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
            background: var(--bg-secondary);
            border-radius: 8px;
            box-shadow: 0 4px 12px var(--shadow);
            overflow: hidden;
            border: 1px solid var(--border-color);
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }

        .header {
            background: var(--bg-secondary);
            color: var(--text-primary);
            padding: 25px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--border-color);
            position: relative;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }

        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .progress-info {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
            color: var(--text-primary);
            font-weight: 600;
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-width: 140px;
            max-width: 160px;
        }

        .progress-info .progress-number {
            color: var(--link-color);
        }

        .progress-info > div:first-child {
            display: flex;
            justify-content: space-between;
            align-items: center;
            white-space: nowrap;
        }

        .progress-bar-container {
            width: 100%;
            height: 6px;
            background: var(--bg-secondary);
            border-radius: 3px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--link-color), var(--link-hover));
            border-radius: 3px;
            transition: width 0.3s ease;
            min-width: 2px;
        }

        [data-theme="dark"] .progress-bar-fill {
            background: linear-gradient(90deg, #238636, #2ea043);
        }

        [data-theme="light"] .progress-bar-fill {
            background: linear-gradient(90deg, #2da44e, #2c974b);
        }

        .theme-toggle {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 12px;
            cursor: pointer;
            color: var(--text-primary);
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }

        .theme-toggle:hover {
            background: var(--bg-hover);
            border-color: var(--link-color);
        }

        .theme-toggle svg {
            width: 16px;
            height: 16px;
            fill: currentColor;
        }

        .header h1 {
            font-size: 1.6em;
            font-weight: 700;
            color: var(--text-title);
            transition: color 0.3s ease;
        }

        .complete-button {
            color: #ffffff;
            text-decoration: none;
            padding: 12px 20px;
            background: var(--button-bg);
            border-radius: 6px;
            transition: all 0.2s;
            font-size: 0.95em;
            font-weight: 600;
            border: 1px solid var(--button-bg);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            flex: 0 0 auto;
        }

        .complete-button:hover {
            background: var(--button-hover);
            border-color: var(--button-hover);
        }

        .complete-button.completed {
            background: #2da44e;
            border-color: #2da44e;
        }

        [data-theme="dark"] .complete-button.completed {
            background: #3fb950;
            border-color: #3fb950;
        }

        .complete-button.completed:hover {
            background: #2c974b;
            border-color: #2c974b;
        }

        [data-theme="dark"] .complete-button.completed:hover {
            background: #56d364;
            border-color: #56d364;
        }

        .back-link {
            color: #ffffff;
            text-decoration: none;
            padding: 10px 20px;
            background: #57606a;
            border-radius: 6px;
            transition: all 0.2s;
            font-size: 0.95em;
            font-weight: 600;
            border: 1px solid #57606a;
        }

        [data-theme="light"] .back-link {
            background: #656d76;
            border-color: #656d76;
        }

        .back-link:hover {
            background: #6e7781;
            border-color: #6e7781;
        }

        [data-theme="light"] .back-link:hover {
            background: #768390;
            border-color: #768390;
        }

        .nav-buttons {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 40px;
            padding-top: 30px;
            border-top: 2px solid var(--border-color);
            gap: 20px;
        }

        .nav-button {
            flex: 1;
            padding: 12px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.95em;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
            border: 1px solid var(--border-color);
        }

        .nav-button.prev {
            background: var(--bg-secondary);
            color: var(--text-primary);
            justify-content: flex-start;
        }

        .nav-button.next {
            background: var(--link-color);
            color: #ffffff;
            justify-content: flex-end;
        }

        .nav-button.prev:hover {
            background: var(--bg-hover);
            border-color: var(--link-color);
        }

        .nav-button.next:hover {
            background: var(--link-hover);
        }

        .nav-button.disabled {
            opacity: 0.5;
            cursor: not-allowed;
            pointer-events: none;
        }

        .nav-button-title {
            font-weight: 600;
        }

        .nav-button-label {
            font-size: 0.85em;
            opacity: 0.8;
        }

        .nav-button.prev .nav-button-label {
            order: -1;
        }

        .markdown-body {
            padding: 50px;
            min-height: 400px;
            color: var(--text-primary);
            background: var(--bg-primary);
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        .markdown-body h1 {
            color: var(--text-title);
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 12px;
            margin-top: 30px;
            margin-bottom: 25px;
            font-weight: 700;
            font-size: 2em;
            transition: all 0.3s ease;
        }

        .markdown-body h2 {
            color: var(--text-title);
            margin-top: 35px;
            margin-bottom: 18px;
            padding-left: 12px;
            border-left: 4px solid var(--link-color);
            font-weight: 700;
            font-size: 1.5em;
            transition: all 0.3s ease;
        }

        .markdown-body h3 {
            color: var(--text-title);
            margin-top: 28px;
            margin-bottom: 15px;
            font-weight: 600;
            font-size: 1.25em;
            transition: color 0.3s ease;
        }

        .markdown-body p {
            margin-bottom: 18px;
            line-height: 1.8;
            color: var(--text-primary);
            transition: color 0.3s ease;
        }

        .markdown-body ul, .markdown-body ol {
            margin-bottom: 18px;
            padding-left: 35px;
        }

        .markdown-body li {
            margin-bottom: 10px;
            color: var(--text-primary);
            line-height: 1.7;
            transition: color 0.3s ease;
        }

        .markdown-body blockquote {
            border-left: 4px solid var(--border-color);
            margin: 25px 0;
            color: var(--text-secondary);
            background: var(--bg-secondary);
            padding: 18px 25px;
            border-radius: 4px;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        .markdown-body table {
            border-collapse: collapse;
            width: 100%;
            margin: 25px 0;
            box-shadow: 0 2px 8px var(--shadow);
            border: 1px solid var(--border-color);
            transition: border-color 0.3s ease;
        }

        .markdown-body table th {
            background: var(--bg-tertiary);
            color: var(--text-title);
            padding: 14px;
            text-align: left;
            font-weight: 700;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        .markdown-body table td {
            padding: 12px 14px;
            border-bottom: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            color: var(--text-primary);
            transition: all 0.3s ease;
        }

        .markdown-body table tr:nth-child(even) {
            background: var(--bg-secondary);
            transition: background-color 0.3s ease;
        }

        .markdown-body table tr:hover {
            background: var(--bg-hover);
            transition: background-color 0.3s ease;
        }
        /* 代码块样式 */
        .markdown-body pre {
            background: var(--bg-code);
            border-radius: 6px;
            padding: 20px;
            overflow-x: auto;
            margin: 25px 0;
            box-shadow: 0 4px 12px var(--shadow);
            position: relative;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        /* 浅色模式下代码块使用更深的背景 */
        [data-theme="light"] .markdown-body pre {
            background: #f6f8fa;
            border: 1px solid #d8dee4;
        }

        [data-theme="light"] .highlight pre {
            background: #f6f8fa;
            border: 1px solid #d8dee4;
        }

        .markdown-body pre code {
            background: transparent;
            padding: 0;
            color: var(--text-primary);
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
            font-size: 0.95em;
            line-height: 1.7;
        }

        /* 行内代码样式 */
        .markdown-body code:not(pre code) {
            background: var(--bg-tertiary);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            color: var(--link-color);
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        /* Pygments 语法高亮样式 */
        .highlight {
            margin: 25px 0;
        }

        .highlight pre {
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        /* Dark theme syntax colors */
        [data-theme="dark"] .highlight .k { color: #ff7b72; font-weight: bold; }
        [data-theme="dark"] .highlight .kd { color: #ff7b72; font-weight: bold; }
        [data-theme="dark"] .highlight .kt { color: #79c0ff; font-weight: bold; }
        [data-theme="dark"] .highlight .kn { color: #ff7b72; font-weight: bold; }
        [data-theme="dark"] .highlight .kc { color: #79c0ff; font-weight: bold; }
        [data-theme="dark"] .highlight .s { color: #a5d6ff; }
        [data-theme="dark"] .highlight .s1 { color: #a5d6ff; }
        [data-theme="dark"] .highlight .s2 { color: #a5d6ff; }
        [data-theme="dark"] .highlight .s3 { color: #a5d6ff; }
        [data-theme="dark"] .highlight .sb { color: #a5d6ff; }
        [data-theme="dark"] .highlight .c { color: #8b949e; font-style: italic; }
        [data-theme="dark"] .highlight .c1 { color: #8b949e; font-style: italic; }
        [data-theme="dark"] .highlight .cm { color: #8b949e; font-style: italic; }
        [data-theme="dark"] .highlight .cp { color: #8b949e; font-style: italic; }
        [data-theme="dark"] .highlight .mi { color: #79c0ff; }
        [data-theme="dark"] .highlight .mf { color: #79c0ff; }
        [data-theme="dark"] .highlight .mh { color: #79c0ff; }
        [data-theme="dark"] .highlight .nf { color: #d2a8ff; }
        [data-theme="dark"] .highlight .na { color: #79c0ff; }
        [data-theme="dark"] .highlight .nc { color: #79c0ff; font-weight: bold; }
        [data-theme="dark"] .highlight .o { color: #ff7b72; }
        [data-theme="dark"] .highlight .ow { color: #ff7b72; }
        [data-theme="dark"] .highlight .n { color: #c9d1d9; }
        [data-theme="dark"] .highlight .nb { color: #79c0ff; }
        [data-theme="dark"] .highlight .bp { color: #79c0ff; }
        [data-theme="dark"] .highlight .p { color: #c9d1d9; }
        [data-theme="dark"] .highlight .err { color: #f85149; background: #490202; font-weight: bold; }
        [data-theme="dark"] .highlight .vi { color: #79c0ff; }
        [data-theme="dark"] .highlight .vg { color: #79c0ff; }
        [data-theme="dark"] .highlight .nn { color: #79c0ff; }

        /* Light theme syntax colors - 增强对比度，确保清晰可见 */
        [data-theme="light"] .highlight .k { color: #cf222e; font-weight: bold; }
        [data-theme="light"] .highlight .kd { color: #cf222e; font-weight: bold; }
        [data-theme="light"] .highlight .kt { color: #0550ae; font-weight: bold; }
        [data-theme="light"] .highlight .kn { color: #cf222e; font-weight: bold; }
        [data-theme="light"] .highlight .kc { color: #0550ae; font-weight: bold; }
        [data-theme="light"] .highlight .s { color: #0a3069; font-weight: 500; }
        [data-theme="light"] .highlight .s1 { color: #0a3069; font-weight: 500; }
        [data-theme="light"] .highlight .s2 { color: #0a3069; font-weight: 500; }
        [data-theme="light"] .highlight .s3 { color: #0a3069; font-weight: 500; }
        [data-theme="light"] .highlight .sb { color: #0a3069; font-weight: 500; }
        [data-theme="light"] .highlight .c { color: #6e7781; font-style: italic; font-weight: 500; }
        [data-theme="light"] .highlight .c1 { color: #6e7781; font-style: italic; font-weight: 500; }
        [data-theme="light"] .highlight .cm { color: #6e7781; font-style: italic; font-weight: 500; }
        [data-theme="light"] .highlight .cp { color: #6e7781; font-style: italic; font-weight: 500; }
        [data-theme="light"] .highlight .mi { color: #0550ae; font-weight: 600; }
        [data-theme="light"] .highlight .mf { color: #0550ae; font-weight: 600; }
        [data-theme="light"] .highlight .mh { color: #0550ae; font-weight: 600; }
        [data-theme="light"] .highlight .nf { color: #8250df; font-weight: 600; }
        [data-theme="light"] .highlight .na { color: #0550ae; font-weight: 600; }
        [data-theme="light"] .highlight .nc { color: #0550ae; font-weight: bold; }
        [data-theme="light"] .highlight .o { color: #cf222e; font-weight: 600; }
        [data-theme="light"] .highlight .ow { color: #cf222e; font-weight: 600; }
        [data-theme="light"] .highlight .n { color: #24292f; font-weight: 500; }
        [data-theme="light"] .highlight .nb { color: #0550ae; font-weight: 600; }
        [data-theme="light"] .highlight .bp { color: #0550ae; font-weight: 600; }
        [data-theme="light"] .highlight .p { color: #24292f; font-weight: 500; }
        [data-theme="light"] .highlight .err { color: #82071e; background: #ffebe9; font-weight: bold; }
        [data-theme="light"] .highlight .vi { color: #0550ae; font-weight: 600; }
        [data-theme="light"] .highlight .vg { color: #0550ae; font-weight: 600; }
        [data-theme="light"] .highlight .nn { color: #0550ae; font-weight: bold; }

        /* 浅色模式下代码文本基础颜色增强 */
        [data-theme="light"] .markdown-body pre code {
            color: #24292f;
            font-weight: 400;
        }

        [data-theme="light"] .highlight pre {
            color: #24292f;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
            <div class="header-actions">
                <div class="progress-info">
                    <div>
                        <span>进度:</span>
                        <span class="progress-number" id="progressText">0/0</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" id="progressBar" style="width: 0%;"></div>
                    </div>
                </div>
                <button class="theme-toggle" id="themeToggle" aria-label="切换主题">
                    <svg id="themeIcon" viewBox="0 0 16 16" width="16" height="16">
                        <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM2 8a6 6 0 0 1 6-6v12a6 6 0 0 1-6-6Z"></path>
                    </svg>
                    <span id="themeText">浅色</span>
                </button>
                <a href="/" class="back-link">← 返回目录</a>
            </div>
        </div>
        <div class="markdown-body markdown-body">
            {{ content|safe }}

            <div class="nav-buttons">
                {% if prev_module %}
                <a href="/view/{{ prev_module.id }}" class="nav-button prev">
                    <span class="nav-button-label">上一页</span>
                    <span class="nav-button-title">← {{ prev_module.title }}</span>
                </a>
                {% else %}
                <div class="nav-button prev disabled">
                    <span class="nav-button-label">上一页</span>
                    <span class="nav-button-title">← 已经是第一页</span>
                </div>
                {% endif %}

                <button class="complete-button" id="completeButton" data-module-id="{{ module_id }}">
                    <span id="completeIcon">✓</span>
                    <span id="completeText">标记完成</span>
                </button>

                {% if next_module %}
                <a href="/view/{{ next_module.id }}" class="nav-button next">
                    <span class="nav-button-title">{{ next_module.title }} →</span>
                    <span class="nav-button-label">下一页</span>
                </a>
                {% else %}
                <div class="nav-button next disabled">
                    <span class="nav-button-title">已经是最后一页 →</span>
                    <span class="nav-button-label">下一页</span>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
    <script>
        (function() {
            const themeToggle = document.getElementById('themeToggle');
            const themeIcon = document.getElementById('themeIcon');
            const themeText = document.getElementById('themeText');
            const html = document.documentElement;
            const completeButton = document.getElementById('completeButton');
            const completeIcon = document.getElementById('completeIcon');
            const completeText = document.getElementById('completeText');
            const moduleId = completeButton.dataset.moduleId;
            const progressText = document.getElementById('progressText');

            // 从 localStorage 读取主题偏好，默认为 dark
            const currentTheme = localStorage.getItem('theme') || 'dark';
            html.setAttribute('data-theme', currentTheme);
            updateThemeIcon(currentTheme);

            themeToggle.addEventListener('click', function() {
                const current = html.getAttribute('data-theme');
                const newTheme = current === 'dark' ? 'light' : 'dark';
                html.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
                updateThemeIcon(newTheme);
            });

            function updateThemeIcon(theme) {
                if (theme === 'dark') {
                    themeIcon.innerHTML = '<path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM2 8a6 6 0 0 1 6-6v12a6 6 0 0 1-6-6Z"></path>';
                    themeText.textContent = '浅色';
                } else {
                    themeIcon.innerHTML = '<path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0-1.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5ZM8 0a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0V.75A.75.75 0 0 1 8 0ZM8 13.5a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 8 13.5ZM2.343 2.343a.75.75 0 0 1 1.061 0l1.06 1.061a.75.75 0 0 1-1.06 1.06l-1.061-1.06a.75.75 0 0 1 0-1.061Zm9.193 9.193a.75.75 0 0 1 1.06 0l1.061 1.06a.75.75 0 0 1-1.06 1.061l-1.061-1.06a.75.75 0 0 1 0-1.061ZM0 8a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5H.75A.75.75 0 0 1 0 8Zm13.5 0a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5h-1.5A.75.75 0 0 1 13.5 8ZM2.343 13.657a.75.75 0 0 1 0-1.061l1.061-1.06a.75.75 0 0 1 1.06 1.06l-1.06 1.061a.75.75 0 0 1-1.061 0Zm9.193-9.193a.75.75 0 0 1 0-1.06l1.06-1.061a.75.75 0 1 1 1.061 1.06l-1.061 1.061a.75.75 0 0 1-1.06 0Z"></path>';
                    themeText.textContent = '深色';
                }
            }

            // 学习进度管理
            function getProgress() {
                const progress = localStorage.getItem('learningProgress');
                return progress ? JSON.parse(progress) : {};
            }

            function saveProgress(progress) {
                localStorage.setItem('learningProgress', JSON.stringify(progress));
            }

            function updateCompleteButton() {
                const progress = getProgress();
                const isCompleted = progress[moduleId] === true;

                if (isCompleted) {
                    completeButton.classList.add('completed');
                    completeIcon.textContent = '✓';
                    completeText.textContent = '已完成';
                } else {
                    completeButton.classList.remove('completed');
                    completeIcon.textContent = '';
                    completeText.textContent = '标记完成';
                }
            }

            function updateProgress() {
                const progress = getProgress();
                // 从localStorage获取模块总数（由主页设置）
                const totalModules = parseInt(localStorage.getItem('totalModules')) || 0;
                let completed = 0;

                // 计算已完成的数量
                for (const id in progress) {
                    if (progress[id] === true) {
                        completed++;
                    }
                }

                progressText.textContent = completed + '/' + totalModules;

                // 更新进度条
                const progressBar = document.getElementById('progressBar');
                if (progressBar && totalModules > 0) {
                    const percentage = (completed / totalModules) * 100;
                    progressBar.style.width = percentage + '%';
                }
            }

            // 初始化完成按钮状态和进度
            updateCompleteButton();
            updateProgress();

            // 点击完成按钮
            completeButton.addEventListener('click', function() {
                const progress = getProgress();
                const isCompleted = progress[moduleId] === true;
                progress[moduleId] = !isCompleted;
                saveProgress(progress);
                updateCompleteButton();
                updateProgress();
            });
        })();
    </script>
</body>
</html>
"""


def load_yaml_data():
    """加载 YAML 文件数据"""
    with open(YAML_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def organize_modules_by_section(modules):
    """按注释中的部分组织模块"""
    # 读取原始 YAML 文件来提取注释信息
    section_info = []
    with open(YAML_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

        # 找到所有部分标记
        for i, line in enumerate(lines):
            if '==========' in line and '部分' in line:
                # 提取部分标题（例如："第一部分：Flink基础概念"）
                # 格式: # ========== 第一部分：Flink基础概念 ==========
                if '：' in line:
                    parts = line.split('：')
                    if len(parts) >= 2:
                        # 获取"第一部分"等前缀
                        prefix = parts[0].split('=')[-1].strip()
                        # 获取标题部分
                        title_part = parts[1].split('=')[0].strip()
                        title = f"{prefix}：{title_part}"
                    else:
                        title = line.split('=')[1].strip() if '=' in line else line.strip()
                else:
                    # 如果没有冒号，直接提取标题
                    title = line.split('=')[1].strip() if '=' in line else line.strip()

                # 查找这个标记后的第一个模块 id
                for j in range(i + 1, min(i + 20, len(lines))):
                    if 'id:' in lines[j]:
                        module_id = lines[j].split('id:')[1].strip()
                        section_info.append({
                            'title': title,
                            'first_module_id': module_id
                        })
                        break

    # 组织模块到各个 section
    sections = []
    module_id_to_index = {m['id']: i for i, m in enumerate(modules)}

    for i, info in enumerate(section_info):
        start_idx = module_id_to_index.get(info['first_module_id'])
        if start_idx is None:
            continue

        # 找到下一个 section 的起始位置，或者到末尾
        end_idx = len(modules)
        if i + 1 < len(section_info):
            next_start = module_id_to_index.get(section_info[i + 1]['first_module_id'])
            if next_start is not None:
                end_idx = next_start

        sections.append({
            'title': info['title'],
            'modules': modules[start_idx:end_idx]
        })

    return sections


@app.route('/')
def index():
    """主页：显示学习路径目录"""
    data = load_yaml_data()
    learning_path = data['learning_path']

    sections = organize_modules_by_section(learning_path['modules'])

    return render_template_string(
        HOME_TEMPLATE,
        title=learning_path['title'],
        description=learning_path['description'],
        sections=sections
    )


@app.route('/view/<module_id>')
def view_markdown(module_id):
    """查看指定模块的 Markdown 文件"""
    md_file = OUTPUT_DIR / f"{module_id}.md"

    if not md_file.exists():
        abort(404)

    # 读取 Markdown 文件
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # 转换为 HTML，启用语法高亮
    html_content = markdown.markdown(
        md_content,
        extensions=[
            'fenced_code',
            'tables',
            'codehilite',
            'nl2br',
            'sane_lists'
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': True,
                'noclasses': False,
                'linenums': False
            }
        }
    )

    # 获取模块标题（从 YAML 中）
    data = load_yaml_data()
    modules = data['learning_path']['modules']
    module_info = next((m for m in modules if m['id'] == module_id), None)
    title = module_info['title'] if module_info else module_id

    # 找到当前模块的前一个和后一个模块
    prev_module = None
    next_module = None
    for i, module in enumerate(modules):
        if module['id'] == module_id:
            if i > 0:
                prev_module = modules[i - 1]
            if i < len(modules) - 1:
                next_module = modules[i + 1]
            break

    return render_template_string(
        MARKDOWN_TEMPLATE,
        title=title,
        content=html_content,
        module_id=module_id,
        prev_module=prev_module,
        next_module=next_module
    )


if __name__ == '__main__':
    import sys
    # 默认使用 8080 端口
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"启动服务器...")
    print(f"访问 http://localhost:{port} 查看学习路径")
    app.run(host='0.0.0.0', port=port, debug=True)

