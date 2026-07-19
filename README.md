# BearmeCoffee 订单数据大盘

将网店订单 Excel 上传、完整呈现订单明细的数据大盘。前端 Vue 3 + Element Plus，后端 Python FastAPI，数据库 MySQL 8.0（容器化）。

## 功能

- Excel 拖拽上传（`.xlsx` / `.xlsm`），单文件上限 50MB
- 自动解析"一订单多行"结构：订单级字段向下填充到每个商品明细行
- 全量数据呈现：20 列表格 + 分页 + 筛选（订单号 / 门店 / 来源 / 状态 / 商品名）+ 排序
- 顶部统计卡片：数据行数 / 订单数 / 总金额 / 门店数
- 每次上传**全量替换**已有数据（清空后重新插入）

## 目录结构

```
bearMeCoffeeProject/
├── 网店订单.xlsx              # 样本数据
├── docker-compose.yml         # MySQL 8.0 容器
├── docker/init.sql            # 建表脚本（容器首启自动执行）
├── scripts/
│   ├── setup-mysql.sh         # 一键准备容器运行时 + MySQL
│   └── dev.sh                 # 同时启动前后端
├── backend/                    # FastAPI + openpyxl + PyMySQL
└── frontend/                   # Vue 3 + Vite + Element Plus
```

## 环境要求

| 组件 | 最低版本 | 说明 |
|---|---|---|
| Python | 3.9+ | 系统自带即可 |
| Node.js | 18+ | 前端构建 |
| Docker 运行时 | — | 由 setup 脚本自动安装 Colima（macOS） |

## 快速开始

### 1. 启动 MySQL

```bash
bash scripts/setup-mysql.sh
```

脚本会自动处理（幂等，可重复运行）：
- 检测/安装 Homebrew（首次会请求 sudo 密码）
- 安装 Colima + Docker CLI + docker-compose
- 启动 Colima + MySQL 8.0 容器
- 等待就绪并校验 `coffee_orders` 表

> 若你已安装 Docker Desktop，脚本会跳过 Colima 直接使用。

### 2. 启动前后端

```bash
bash scripts/dev.sh
```

- 前端：<http://localhost:5173>
- 后端 API 文档：<http://localhost:8000/docs>

### 3. 使用

1. 浏览器打开 <http://localhost:5173>
2. 拖拽 `网店订单.xlsx` 到上传区
3. 导入完成后，统计卡片与表格自动刷新
4. 表格可分页、按列排序、用顶部条件筛选

## 数据库连接

| 项 | 值 |
|---|---|
| host | localhost |
| port | 3306 |
| database | coffee |
| user | coffee |
| password | coffee123 |
| root password | root123 |

## API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/upload` | 上传 Excel，全量替换导入 |
| GET | `/api/orders` | 分页查询 `?page=&size=&order_no=&store=&source=&status=&product=&sort=&dir=` |
| GET | `/api/orders/filters` | 下拉选项（门店/来源/状态去重值） |
| GET | `/api/orders/stats` | 统计摘要 |
| GET | `/api/health` | 健康检查 |

## 数据模型

表 `coffee_orders`，20 个业务列 + `id` / `is_order_header` / `imported_at`。`is_order_header=1` 标记订单头行（含订单总金额），用于统计总金额。

## 常见问题

**Q: 重新上传会丢失之前的数据吗？**
A: 是。每次上传执行 `TRUNCATE` 后重新插入，确保大盘反映最新文件内容。这是设计如此。

**Q: 想换一个 Excel 文件结构怎么办？**
A: 修改 `docker/init.sql` 的建表语句与 `backend/app/services/importer.py` 的列映射。如需重新初始化表结构，删除 `docker/mysql-data` 卷让容器重新初始化。

**Q: MySQL 启动很慢？**
A: 首次需拉取镜像 + 初始化，约 30–60 秒。后续启动约 10 秒。可 `docker compose logs -f mysql` 查看进度。

**Q: 后端能在 MySQL 没启动时运行吗？**
A: 能。后端用懒连接（每次请求才打开连接），MySQL 不可用时 `/api/health` 返回 `degraded`，但服务本身正常启动。上传/查询等涉及数据库的接口会返回连接错误。
