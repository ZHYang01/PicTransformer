# PicTransformer

一款简洁高效的在线图片处理工具 / A simple and efficient online image processing tool

---

## 功能介绍 / Features

### 图片格式转换 / Image Format Conversion
将任意图片格式一键转换为 JPEG 格式 / Convert any image format to JPEG with one click

- 支持 PNG、JPG、BMP、GIF、TIFF、WebP、HEIC 等常见格式 / Supports PNG, JPG, BMP, GIF, TIFF, WebP, HEIC
- 可调节输出质量，平衡文件大小与画质 / Adjustable output quality
- 批量转换，一次处理多张图片 / Batch conversion support
- 透明背景自动填充白色 / Transparent background auto-filled with white

### PDF 合并 / PDF Merger
将多个 PDF 文件合并为一个 / Merge multiple PDF files into one

- 支持拖拽上传，操作便捷 / Drag and drop upload
- 快速合并多个 PDF 为单个文件 / Quickly merge multiple PDFs
- 保留原始文件内容与排版 / Preserve original content and layout

---

## 技术说明 / Technical Details

- 基于 Python Flask 框架开发 / Built with Python Flask framework
- 图片处理使用 Pillow 库 / Image processing with Pillow
- PDF 处理使用 pypdf 库 / PDF processing with pypdf
- 纯本地运行，无需上传至服务器 / Pure local operation, no server upload required

## 安装依赖 / Installation

```bash
pip install -r requirements.txt
```

---

## 启动服务 / Quick Start

```bash
./start.sh
```

停止服务 / Stop: 在终端按 `Ctrl+C` / Press `Ctrl+C` in terminal
