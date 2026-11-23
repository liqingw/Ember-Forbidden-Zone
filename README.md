# 余烬禁区（v4.0）

一款 2D 俯视角 Roguelike 生存射击游戏，包含 **Python（`pygame-ce`）桌面版** 与 **单文件 HTML5 网页版**（逻辑分辨率 `640×360`）。

- **关卡规模**：4 章主线 + 2 个隐藏副本 + 1 个奖励延续副本（共 35 关 + 收尾）
- **核心系统**：8 名可选角色、104 把武器（7 档品质）、21 个局内天赋、局外永久养成、饮料/商店/宝箱与污染减益机制

---

## 环境准备

- **Python 3.11+**（桌面版运行与数据导出）
  ```bash
  pip install pygame-ce
  ```
- **Node.js**（运行网页版无头自动化自检）
- **Git**（多人协作与版本管理）

---

## 快速启动

在仓库根目录下运行：

- **启动桌面版**：
  ```bash
  python src/main.py
  ```
- **运行桌面版启动自检**：
  ```bash
  python src/main.py --selfcheck
  ```
- **试玩网页版**：直接用浏览器打开 `web/index.html`，或启动一个静态服务器访问 `web/` 目录。

---

## 目录结构一览

| 目录 / 文件 | 说明 |
| :--- | :--- |
| `src/main.py` | Python 桌面版启动入口 |
| `src/sk/` | Python 核心源码，也是数值与武器等配置的**单一事实来源** |
| `web_src/` | 网页版前端源码（`game.js`、`shell.html`、`touch.js` 等）与导出的 `data.js` |
| `web/` | 打包生成的单文件 HTML5 网页版（`index.html`、`manifest.webmanifest`） |
| `mobile_native/` | Android / iOS 移动端壳工程目录（同步放置打包后的网页端文件） |
| `tools/` | 数据导出、网页打包、资源生成与自动化测试脚本 |
| `tests/` | 单元测试 |
| `assets/` | 贴图、字体与音效资源 |
| `使用手册.md` / `游玩手册.md` / `更新日志.md` | 玩法说明与版本变更记录 |

---

## 修改代码后：同步网页版与自检

如果修改了 `src/sk/` 下的数值、武器或关卡数据，需要同步导出给网页版后再验证：

### 1. 同步导出与打包网页版
```bash
python tools/gen_data_js.py
python tools/build_web.py
```

### 2. 运行全套自检
```bash
python -m unittest discover -s tests -v
python src/main.py --selfcheck
python tools/selftest.py
node tools/web_selftest.js
```

---

## 双人协作规范（避坑指南）

### 1. 克隆仓库
```bash
git clone https://github.com/liqingw/Ember-Forbidden-Zone.git
cd Ember-Forbidden-Zone
```

### 2. 日常开发流程（分支 + Pull Request）
不要两个人同时直接往 `main` 硬推代码：

1. **每次开工前先拉取最新代码**：
   ```bash
   git checkout main
   git pull
   ```
2. **创建自己的功能分支**：
   ```bash
   git checkout -b feat-xxx
   ```
3. **开发、自检并推送分支**：
   ```bash
   git add -A
   git commit -m "描述你的改动"
   git push -u origin feat-xxx
   ```
4. **在 GitHub 提 Pull Request 合并**：推送后在仓库页面点 **Compare & pull request**，确认无误后合并到 `main`。

### 3. 关键避坑：避免生成物冲突
`web_src/data.js`、`web/index.html` 与 `mobile_native/` 都是构建脚本自动生成的成品，**不要两个人在不同分支各自打包后再合并**（大文件极易产生大量冲突）。

- **推荐分工**：各自开发只提交 `src/sk/*.py`、`web_src/game.js`、`tests/` 等源码改动；合入 `main` 后，由其中一人拉取最新 `main` 统一运行 `python tools/gen_data_js.py` 和 `python tools/build_web.py` 提交更新。
- 如果误碰冲突：直接删掉冲突产物，拉取最新 `main` 后重新执行导出与构建命令覆盖即可。
