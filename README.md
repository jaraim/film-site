# 🎬 极简影视（Django 影视站）

一个用 **Python + Django** 开发的轻量影视站，对标苹果 CMS(MacCMS10) 的核心体验：分类浏览、搜索、详情、**通用播放器**（跳片头/片尾、倍速、连播、资源切换），并内置了对接苹果 CMS `provide/vod` 标准接口的采集器。

> ⚠️ 仅供学习与技术演示。采集第三方资源请遵守版权与平台规则，本站不内置任何盗版内容。

---

## ✨ 功能特性

### 站点
- 首页（最近更新 + 分类 + 热播）
- 分类页（按类型/年份/热度筛选）
- 详情页（导演/主演/简介/相关推荐）
- 全局搜索（片名/导演/演员模糊匹配）
- **用户 + 积分系统**（注册/登录/签到/充值/付费观看）
- Django Admin 后台管理（`/admin/`）

### 通用播放器（`static/player/film-player.js`，原生 JS，无第三方依赖）
- **跳片头**：自动跳过片头 N 秒（可在播放器设置面板调整，设置持久化到 localStorage）
- **跳片尾**：接近结尾自动跳到结局
- **播放倍速**：0.5x ~ 2.0x 循环切换，支持自定义
- **连播**：本线路自动播下一集；末集自动切换下一线路
- **资源切换**：多播放源（线路）下拉切换，保留当前集数
- **进度记忆**：按「视频+线路+集数」记住播放进度，下次继续
- **快捷键**：空格播放/暂停、←→ ±10秒、↑↓ 音量
- 片头/片尾秒数也可在站点后台按片配置（`Video.skip_intro / skip_outro`）

---

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python manage.py makemigrations videos
python manage.py migrate

# 3. 创建管理员（可选，访问后台用）
python manage.py createsuperuser

# 4. 启动服务
python manage.py runserver 0.0.0.0:8000
```

访问：`http://127.0.0.1:8000/` ，后台 `http://127.0.0.1:8000/admin/`

> 仓库不包含 `db.sqlite3`，首次需先执行迁移再采集或手动造数据。

---

## 👤 用户与积分系统

对标苹果 CMS 会员积分，实现完整积分闭环：

| 能力 | 说明 |
|---|---|
| 注册 / 登录 / 登出 | Django 内置认证，导航右上角入口 |
| 注册奖励 | 新用户注册自动赠送 **100 积分** |
| 每日签到 | 每天可签到 +5 积分（防重复） |
| 积分充值 | 演示充值（+100/+500/+1000/+5000），正式部署接支付 |
| 付费观看 | 影片设置 `need_points`，观看扣费解锁，**重复观看不重复扣费** |
| 积分不足 | 自动跳转用户中心并提示签到/充值 |
| 积分流水 | 完整记录注册/签到/充值/扣费明细及变动后余额 |
| 用户中心 | 余额、累计签到、最近流水、已解锁影片一览 |

**数据模型**（`member` app）
- `Profile`：积分余额、累计签到、最近签到日（一对一扩展 User）
- `PointRecord`：积分流水（类型/变动值/余额/备注）
- `VideoAccess`：已解锁付费片（user+video 唯一）

**付费片配置**：后台 `/admin/` → 影视 → 勾选/输入 `观看所需积分`；或在采集入库后设置 `Video.need_points`。

**积分规则（可在代码调整）**
- 注册奖励 100：`member/apps.py` 信号中 `points=100`
- 每日签到 5：`member/views.py` `checkin()` 中 `+5`
- 付费扣费：`videos/views.py` `play()` 鉴权逻辑

---

## 📦 数据采集（对接苹果 CMS provide/vod 接口）

```bash
# JSON 格式列表采集（不带播放数据）
python manage.py collect --api "http://api.ffzyapi.com/api.php/provide/vod/at/json/" --pages 3

# XML 格式
python manage.py collect --api "http://api.ffzyapi.com/api.php/provide/vod/at/xml/" --pages 3

# 采集并逐个请求 detail 接口补齐播放地址（推荐，可播）
python manage.py collect --api "http://api.ffzyapi.com/api.php/provide/vod/at/json/" --pages 1 --detail

# 仅采集指定来源
python manage.py collect --api "..." --from feifan

# 短剧源：列表用 xml，detail 用 json（json detail 才返回可播地址）
python manage.py collect --api "http://cj.ffzyapi.com/api.php/provide/vod/from/ffm3u8/at/xml/" \
                          --detail-api "http://cj.ffzyapi.com/api.php/provide/vod/at/json/" \
                          --pages 2 --detail
```

> **实测示例**：`cj.ffzyapi.com` 短剧源，用上述命令可真实采集入库并解析出完整剧集（如「择日飞升」14集）与可播地址。

**参数**
| 参数 | 说明 |
|---|---|
| `--api` | 采集接口地址（必填） |
| `--at` | 返回格式 `json/xml/auto`（默认 auto 自动识别） |
| `--pages` | 采集页数（默认 3） |
| `--detail` | 对每条记录请求 detail 接口补齐播放数据 |
| `--detail-api` | detail 接口地址（默认用 `--api`；若列表为 xml 而 detail 需 json，单独指定） |
| `--from` | 仅采集指定来源标识（如 `feifan`、`ffm3u8`） |
| `--headers` | 附加请求头（JSON 字符串） |

**采集器解析规则**（苹果 CMS 标准格式）
- 多播放源：`vod_play_from` 用 `$$$` 分隔（如 `feifan$$$ffm3u8`）
- 多集地址：`vod_play_url` 中集与集用 `#` 或 `$$$` 分隔，集内 `集名$地址`
- 自动为常见来源标识映射中文线路名（非凡线路/非凡M3U8/优酷/爱奇艺…）

**分类初始化**（两级分类树：电影/电视剧/动漫/短剧 → 细分）
```bash
python manage.py setup_categories
```

### 🖥️ 后台网页采集（推荐）

除命令行外，提供**管理后台网页采集**界面（对标苹果 CMS）：

1. 登录后台 `/admin/`（需 staff 权限）
2. 点击「🎬 前往影视数据采集页面」，或直接访问 `/admin/collect/`
3. 输入接口地址、返回格式、页数、detail 等参数（内置常用采集源预设一键填充）
4. 点击「开始采集」，网页实时显示采集进度与结果统计

> 后台采集每次建议 1-5 页（同步执行，页数多会等待较久）。

---

## ⚙️ 后台系统配置 / 广告 / 播放器（对标 MacCMS10）

`system` 应用提供站点配置、广告位、广告、播放器全局配置，**全部在后台可增删改查**：

| 后台模块 | 说明 |
|---|---|
| **站点配置** | `站点名称/关键词/描述/Logo/底部版权` 键值对，前台全站生效 |
| **广告位** | 8 个预设位置（首页顶/侧边、分类顶、详情顶/底、播放顶/底、搜索顶） |
| **广告** | 每个广告位可挂多个广告，支持**代码广告**与**图片链接广告**，可排序/启停 |
| **播放器配置** | 全站播放器默认值：`默认倍速 / 默认片头跳过 / 默认片尾跳过 / 自动连播` |

- 初始化默认数据：`python manage.py setup_system`（已执行）
- 前台广告容器会自动渲染对应广告位内容；播放页读取播放器配置作为全站默认值，用户侧可再覆盖
- 广告渲染链：后台 `Ad.render()` → `system/services.get_ads_map()` → context processor → 模板 `{% for a in ads_map.<位置> %}{{ a|safe }}{% endfor %}`

---

## 🏗️ 项目结构

```
film-site/
├── manage.py
├── requirements.txt
├── config/                  # Django 项目配置
│   ├── settings.py          # 中文/时区/模板/静态目录
│   └── urls.py
├── videos/                  # 影视应用
│   ├── models.py            # Category / Video / VideoSource
│   ├── views.py             # 首页/分类/详情/播放/搜索
│   ├── urls.py
│   ├── admin.py             # 后台管理
│   └── migrations/
├── collector/               # 采集应用
│   └── management/commands/collect.py   # 苹果CMS采集命令
│   └── management/commands/setup_categories.py  # 初始化分类树
├── member/                  # 会员积分应用
│   ├── models.py            # Profile / PointRecord / VideoAccess
│   ├── views.py             # 注册/登录/签到/充值/用户中心
│   └── urls.py
├── system/                  # 系统配置与广告应用
│   ├── models.py            # SiteConfig / AdSlot / Ad / PlayerConfig
│   ├── services.py          # 广告与播放器配置读取
│   ├── context_processors.py# 全站注入 ads_map/site 配置
│   └── management/commands/setup_system.py  # 初始化默认数据
├── templates/               # 页面模板（暗色主题）
│   ├── base.html
│   └── videos/{home,category,detail,play,search}.html
└── static/player/           # 通用播放器组件
    ├── film-player.js       # 跳片头/片尾·倍速·连播·资源切换
    └── film-player.css
```

---

## 📊 数据模型

- **Category**：分类，支持**两级**（`parent` 自引用）
  - 一级：电影/电视剧/动漫/短剧；二级：如 电影→动作片/喜剧片/…、动漫→国产动漫/海外动漫
- **Video**：影视条目（片名/类型/年份/地区/导演/主演/简介/海报/**片头跳过秒数**/**片尾跳过秒数**/状态/点击量）
- **VideoSource**：播放源（线路标识 `from_flag` / 线路名 / 剧集 `episodes` JSON 数组）

播放页通过 `?from=线路&ep=集数` 定位集，`episodes` 每项为 `{"name":"第1集","url":"..."}`。

分类初始化命令：`python manage.py setup_categories`（见上文采集说明）

---

## 🔧 技术栈

- **后端**：Python 3 + Django 4.2+（当前验证 6.1）
- **数据库**：SQLite（可平滑切换 MySQL/PostgreSQL）
- **采集**：requests + lxml / json
- **播放器**：原生 HTML5 video（无第三方 JS 库，通用可嵌入）
