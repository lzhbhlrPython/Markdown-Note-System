# Markdown Note System

Markdown Note System 是一个基于 Flask 框架构建的轻量级个人笔记管理系统。系统主要采用 Markdown 作为笔记书写格式，实现对笔记的创建、编辑、预览、自动备份等功能，同时提供图片上传和管理功能。系统以文件系统和 JSON 文件为数据存储方式，不依赖传统数据库，追求简单、灵活和高效的设计理念。

## 功能特性

- **项目管理**：支持创建、删除、导入和导出项目。
- **笔记管理**：支持创建、编辑、删除、移动和验证笔记。
- **图片管理**：支持图片上传、删除和图库展示。
- **自动备份**：前端使用 localStorage 自动备份编辑中的笔记，减少意外丢失。
- **数据完整性校验**：通过 SHA256 为笔记生成哈希，在保存笔记时进行校验，防止数据被篡改。

## 安装与运行

### 环境要求

- Python 3.7+
- Flask
- 其他依赖项见 `requirements.txt`

### 安装步骤

1. 克隆项目代码：
    ```sh
    git clone git@github.com:lzhbhlrPython/Markdown-Note-System.git
    cd markdown-note-system
    ```

2. 创建并激活虚拟环境：
    ```sh
    python3 -m venv venv
    source venv/bin/activate  # 对于 Windows 系统，使用 `venv\Scripts\activate`
    ```

3. 安装依赖项：
    ```sh
    pip install -r requirements.txt
    ```

4. 运行 Flask 应用：
    ```sh
    python app.py
    ```


## 使用说明

### 项目管理

- **创建项目**：在首页输入项目名称并点击“创建项目”按钮。
- **删除项目**：在项目卡片上点击“删除”按钮。
- **导入项目**：在首页选择项目压缩包文件并点击“导入项目”按钮。
- **下载项目**：在项目详情页点击“下载项目”按钮。

### 笔记管理

- **创建笔记**：在项目详情页输入笔记标题并点击“创建笔记”按钮。
- **编辑笔记**：点击笔记卡片进入编辑页面，使用 Markdown 语法编辑内容。
- **删除笔记**：在笔记卡片上点击“删除”按钮。
- **移动笔记**：在笔记卡片上点击“移动”按钮并输入目标项目 ID。
- **验证笔记**：在编辑页面点击“检测是否篡改”按钮。

### 图片管理

- **上传图片**：在图库页面选择图片文件并点击“上传图片”按钮。
- **删除图片**：在图片卡片上点击“删除”按钮。
- **复制链接**：在图片卡片上点击“复制链接”按钮。

## 目录结构

```plaintext
markdown-note-system/
├── app.py                            # Flask 应用主文件
├── requirements.txt                  # 依赖项文件
├── templates/                        # HTML 模板文件
│   ├── base.html
│   ├── index.html
│   ├── project_detail.html
│   ├── note_edit.html
│   ├── note_preview.html
│   └── gallery.html
├── static/                           # 静态文件目录
│   └── uploads/                      # 图片上传目录
├── data/                             # 数据存储目录
│   ├── images.json                   # 图片数据文件
│   └── <project_id>/                 # 项目目录
│       ├── metadata.json             # 项目元数据文件
│       └── <note_id>.md              # 笔记文件
├── README.md                         # 项目说明文件
├── LICENSE                           # 许可证文件
└── Markdown Note System Document.zip # 文档(请导入系统查看)
```

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库。
2. 创建一个新的分支 (`git checkout -b feature-branch`)。
3. 提交你的修改 (`git commit -am 'Add new feature'`)。
4. 推送到分支 (`git push origin feature-branch`)。
5. 创建一个 Pull Request。

## 许可证

该项目使用 MIT 许可证。详情请参阅 `LICENSE` 文件。

## 联系方式

如有任何问题或建议，请联系 [lzhbhlrpython](https://pyliubaolin.top/)。


## 待完成
1. 添加更多功能，如搜索、标签、分类等。
2. 夜间模式。

## 贡献列表
1. [lzhbhlrPython](https://github.com/lzhbhlrPython)