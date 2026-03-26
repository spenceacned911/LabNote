# LabNote

我们把 **LabNote** 做成了一款本地优先、双语友好、结构清晰、可以长期维护的 Markdown 桌面编辑器。

它最早来自我们对 **MarkText 架构思路** 的一次 Python 重写实践，但现在它已经不再只是“重写版演示工程”。我们把品牌、界面、交互、表格工具、中文 PDF 导出、项目文档和测试整体等等打磨了一遍，让它更像一个愿意认真维护下去的独立项目。

---
## 📦 下载

已经打包好的 **Windows 和 macOS 版本** 可以在 Releases 页面下载：

👉 https://github.com/jinpengaaaaa-ctrl/LabNote/releases
---

## 项目定位

我们没有把原始 Electron / Vue 工程逐行翻译成 Python，而是利用原项目的核心分层思想，再用 Python 重新组织成一套更适合桌面端长期维护的实现。

我们希望 LabNote 具备这些特质：

- 写 Markdown 时顺手、不折腾
- 看起来干净、现代、专业
- 结构清晰，方便继续迭代
- 先把核心体验做稳，再逐步补齐高级能力

换句话说，LabNote 不是一次性拼出来的“能跑就行”的壳子，而是一套已经能承载后续演进的桌面应用骨架。

---

## 已经完成的重点能力

### 1. UI / UX 重构

我们重新整理了整个界面的视觉和交互节奏，目标不是“堆功能感”，而是“让高频操作更自然”。

这一版已经具备：

- 极简、现代、专业的主界面风格
- 深色 / 浅色主题体系
- 更清晰的区域层级：窗口、侧边栏、标签栏、编辑区、预览区、状态栏彼此分明
- 顶部显眼的模式切换：**编辑模式 / 分栏模式 / 预览模式**
- 左侧侧边栏支持 **Project / Outline / Search**
- 侧边栏与主区域之间支持拖拽分割
- 编辑器与预览器之间支持拖拽分割
- 多标签页带显式 `×` 关闭按钮

### 2. 核心编辑能力

- 多标签 Markdown 编辑
- 新建 / 打开 / 保存 / 另存为 / 从磁盘重载
- 当前行高亮
- 自动保存
- 最近文件
- 会话恢复
- 命令面板
- Focus Mode
- Typewriter Mode
- 项目内全文搜索
- 文档大纲（TOC）
- 中英文一键切换

### 3. Markdown 预览与导出

- 实时预览
- HTML 导出
- PDF 导出
- 常见 Markdown 语法支持：
  - 标题
  - 段落
  - 强调 / 加粗 / 删除线
  - 行内代码 / 代码块
  - 列表 / 任务列表
  - 引用块
  - 表格
  - 链接
  - 脚注（基础显示）

### 4. 表格增强

我们专门把表格相关逻辑抽出来重做了，不再把表格当成普通文本凑活处理。

现在已经支持：

- 解析 Markdown 表格
- 格式化当前表格
- 插入表格模板
- 编辑光标所在表格
- 增删行、增删列、修改表头、修改单元格
- 自动整理列宽
- 中英文混排时按 East Asian Width 处理宽度，尽量减少对不齐的问题
- 预览器用真正的网格方式渲染表格，而不是把它重新塞回一坨纯文本里

默认快捷键：

- `Ctrl + Alt + T`：插入表格模板
- `Ctrl + Alt + E`：编辑当前表格
- `Ctrl + Alt + F`：格式化当前表格

---

## 技术栈

### UI / 桌面层
- **Tkinter / ttk**：桌面主界面、多标签页、菜单、侧边栏、状态栏、弹窗

### Markdown 核心层
- **mistune**：Markdown 解析与 AST 构建
- **Pygments**：代码高亮
- **ReportLab**：PDF 导出

### 基础设施
- `pathlib`：路径管理
- `threading`：轮询式文件监听
- `json`：设置持久化
- `argparse`：CLI 启动入口

我们选择这套组合，不是为了追求“技术名词堆满”，而是因为它够轻、够稳，也方便继续往上叠能力。

---

## 架构设计

我们延续了原始 MarkText 的核心分层思想，把工程拆成三层：

1. **应用层 / 主控层**  
   负责窗口、命令、设置、文件打开保存、文件变更监听

2. **核心层 / 编辑器能力层**  
   负责 Markdown 解析、目录提取、导出、项目搜索、表格处理

3. **UI 层 / 渲染层**  
   负责桌面界面、多标签页、侧边栏、实时预览、命令面板、主题系统

### 与原始架构的对应关系

| 原始层         | 原项目职责                                  | LabNote 对应    |
| -------------- | ------------------------------------------- | --------------- |
| `src/main`     | 应用入口、窗口、文件 IO、设置、命令、快捷键 | `labnote/app/`  |
| `src/muya`     | Markdown 核心、文档变换、导出               | `labnote/core/` |
| `src/renderer` | 编辑器 UI、侧边栏、标签页、交互             | `labnote/ui/`   |

### 当前目录结构

```text
labnote/
├── app/
│   ├── application.py      # 应用入口与生命周期
│   ├── commands.py         # 命令注册表
│   ├── document_manager.py # 文档打开、保存、重载
│   ├── file_watcher.py     # 外部文件轮询监听
│   ├── i18n.py             # 中英文本地化
│   └── settings.py         # 配置持久化
│
├── core/
│   ├── document.py         # 文档状态对象
│   ├── markdown_engine.py  # Markdown -> AST / HTML / TOC
│   ├── exporters.py        # HTML / PDF 导出
│   ├── search.py           # 项目搜索
│   ├── tables.py           # Markdown 表格解析与格式化
│   └── toc.py              # 文档大纲提取
│
└── ui/
    ├── main_window.py      # 主窗口与交互编排
    ├── document_view.py    # 单文档编辑 / 预览视图
    ├── preview_renderer.py # AST -> Tk 预览渲染
    ├── dialogs.py          # 命令面板 / 偏好设置 / 表格工具
    ├── themes.py           # 主题系统
    └── widgets.py          # 可关闭标签栏等自定义控件
```



## 运行方式

### 环境要求

- Python **3.10+**
- Windows / macOS / Linux
- Tkinter 一般随 Python 官方发行版提供

### 安装依赖

```bash
pip install -r requirements.txt
```

### 直接运行

``` bash
python run.py
```

### 作为模块运行

```bash
python -m labnote
```

### 启动时直接打开文件或目录

```bash
python -m labnote demo/example.md
python -m labnote README.md ./demo
```



## 使用说明

### 侧边栏

* **Project**：浏览项目文件树
* **Outline**：浏览当前文档大纲并跳转
* Search：在当前项目里做全文搜索

### 标签页

- 每个标签页右侧都有明确可点的 `×`
- 未保存文档会有脏状态提示

### 偏好设置

当前支持配置：

- 主题
- 界面语言
- 正文字号
- 代码字号
- 行间距
- 默认布局
- 自动保存
- 会话恢复
- 默认显示侧边栏
- 默认专注模式
- 默认打字机模式

### 快捷键

| 功能            | 快捷键         |
| --------------- | -------------- |
| 新建标签        | `Ctrl+N`       |
| 打开文件        | `Ctrl+O`       |
| 打开文件夹      | `Ctrl+Shift+O` |
| 保存            | `Ctrl+S`       |
| 另存为          | `Ctrl+Shift+S` |
| 关闭标签页      | `Ctrl+W`       |
| 命令面板        | `Ctrl+Shift+P` |
| Preferences     | `Ctrl+,`       |
| 切换侧边栏      | `Ctrl+\`       |
| Editor Only     | `Alt+1`        |
| Split           | `Alt+2`        |
| Preview Only    | `Alt+3`        |
| Focus Mode      | `F9`           |
| Typewriter Mode | `F10`          |
| 插入表格模板    | `Ctrl+Alt+T`   |
| 编辑当前表格    | `Ctrl+Alt+E`   |
| 格式化当前表格  | `Ctrl+Alt+F`   |

### 配置文件位置

我们把配置目录统一放在 `labnote` 名下：

- Linux: `~/.config/labnote/settings.json`
- macOS: `~/Library/Application Support/labnote/settings.json`
- Windows: `%APPDATA%/labnote/settings.json`

配置内容包括：

- 主题
- 界面语言
- 字体大小
- 自动保存
- 会话恢复
- 侧边栏状态
- 布局模式
- Focus Mode / Typewriter Mode
- 最近文件
- 上次打开目录
- 窗口大小

### 测试与质量检查

我们给这个版本补了三类基础校验。

#### 1. 编译检查

```
python -m compileall -q .
```

### #### 2. 单元测试

```
python -m unittest discover -s tests -v
```

### #### 3. GUI 冒烟测试

我们在无头环境里验证过这些关键路径：

- 应用启动
- 打开文档
- 模式切换
- 主题切换
- 语言切换
- 项目搜索
- Markdown 表格格式化
- HTML / PDF 导出

## 当前边界

我们很清楚这一版的定位：

它已经是一个**可运行、可维护、可以继续演进的项目骨架**，但还没有覆盖所有高级功能。

目前还没完全覆盖的方向包括：

- 完整 WYSIWYG 编辑体验
- 数学公式渲染
- 图片粘贴与附件管理
- Mermaid / 图表生态
- 更复杂的快捷键系统
- 多窗口支持
- 插件机制
- 更细粒度主题系统
- 自动更新与安装包

------

## 后续可扩展方向

如果继续往前做，我们优先会推进这些：

1. 富文本 / WYSIWYG 编辑模型
2. 数学公式支持
3. 图片与附件管理
4. Mermaid / Vega 图表支持
5. 编辑器能力增强
6. 多窗口
7. 插件系统
8. 主题系统升级
9. 更完整国际化
