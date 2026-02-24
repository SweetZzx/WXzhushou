# 数据库架构文档

> 本文档详细说明微信AI助手项目的数据库设计，适合初学者阅读。

## 目录

1. [数据库概述](#1-数据库概述)
2. [数据表详解](#2-数据表详解)
3. [数据关系图](#3-数据关系图)
4. [常用查询示例](#4-常用查询示例)
5. [数据流转示例](#5-数据流转示例)

---

## 1. 数据库概述

### 1.1 使用什么数据库？

本项目使用 **SQLite** 数据库。

**为什么选择 SQLite？**

| 特点 | 说明 |
|------|------|
| 轻量级 | 整个数据库就是一个文件，不需要安装数据库服务器 |
| 零配置 | 不需要复杂的配置，开箱即用 |
| 可靠性高 | 支持事务，数据不会轻易丢失 |
| 适合小型项目 | 对于几百到几千用户的项目完全够用 |
| 易于备份 | 复制数据库文件就是备份 |

### 1.2 数据库文件位置

```
data/wechat.db
```

### 1.3 数据库有多少张表？

本项目共有 **2 张数据表**：

```
┌─────────────────┐     ┌─────────────────┐
│    schedules    │     │  user_settings  │
│   (日程表)       │     │  (用户设置表)    │
└─────────────────┘     └─────────────────┘
```

---

## 2. 数据表详解

### 2.1 schedules 表（日程表）

**用途**：存储用户创建的所有日程

#### 表结构

| 字段名 | 数据类型 | 说明 | 示例 |
|--------|----------|------|------|
| `id` | INTEGER | 日程的唯一编号（自动生成） | 1, 2, 3... |
| `user_id` | VARCHAR(100) | 用户的微信 OpenID | oKXgA2f3rTVyibzgiX-PEfmXxmUc |
| `title` | VARCHAR(200) | 日程标题 | 开会、刷牙、健身 |
| `description` | TEXT | 日程详细描述（可选） | 项目进度讨论 |
| `scheduled_time` | DATETIME | 日程时间 | 2026-02-14 09:00:00 |
| `remind_before` | INTEGER | 提前多少分钟提醒 | 10 |
| `status` | VARCHAR(20) | 日程状态 | active（有效）/ completed（已完成） |
| `job_id` | VARCHAR(100) | 定时任务ID（内部使用） | schedule_1_12345 |
| `created_at` | DATETIME | 创建时间 | 2026-02-13 10:30:00 |
| `updated_at` | DATETIME | 最后修改时间 | 2026-02-13 11:00:00 |
| `completed_at` | DATETIME | 完成时间（可选） | 2026-02-14 10:00:00 |

#### 字段详解

**id（主键）**
- 每个日程都有一个唯一的数字编号
- 自动递增，不需要手动填写
- 用于修改、删除日程时定位具体的日程

**user_id（用户标识）**
- 存储用户的微信 OpenID
- 微信给每个用户分配的唯一标识符
- 用于区分不同用户的日程（数据隔离）

**status（状态）**
- `active`：日程有效，会正常提醒
- `completed`：日程已完成，不再提醒

#### 数据示例

```
id: 1
user_id: oKXgA2f3rTVyibzgiX-PEfmXxmUc
title: 开会
description: 项目进度讨论
scheduled_time: 2026-02-14 09:00:00
remind_before: 10
status: active
created_at: 2026-02-13 10:30:00
```

---

### 2.2 user_settings 表（用户设置表）

**用途**：存储每个用户的个性化提醒设置

#### 表结构

| 字段名 | 数据类型 | 说明 | 示例 |
|--------|----------|------|------|
| `id` | INTEGER | 设置记录的唯一编号 | 1, 2, 3... |
| `user_id` | VARCHAR(100) | 用户的微信 OpenID | oKXgA2f3rTVyibzgiX-PEfmXxmUc |
| `daily_reminder_enabled` | BOOLEAN | 是否开启每日提醒 | true / false |
| `daily_reminder_time` | VARCHAR(10) | 每日提醒时间 | 08:00 |
| `pre_schedule_reminder_enabled` | BOOLEAN | 是否开启日程前提醒 | true / false |
| `pre_schedule_reminder_minutes` | INTEGER | 日程前多少分钟提醒 | 10 |
| `timezone` | VARCHAR(50) | 用户时区 | Asia/Shanghai |
| `created_at` | DATETIME | 创建时间 | 2026-02-13 10:30:00 |
| `updated_at` | DATETIME | 最后修改时间 | 2026-02-13 11:00:00 |

#### 字段详解

**daily_reminder_enabled（每日提醒开关）**
- `true`（1）：每天早上收到当天日程汇总
- `false`（0）：不收到每日汇总

**daily_reminder_time（每日提醒时间）**
- 格式：HH:MM（24小时制）
- 默认：08:00
- 示例：08:00、09:30、18:00

**pre_schedule_reminder_enabled（日程前提醒开关）**
- `true`（1）：每个日程开始前会提醒
- `false`（0）：不提醒

**pre_schedule_reminder_minutes（提前提醒分钟数）**
- 日程开始前多少分钟提醒
- 默认：10 分钟
- 示例：5、10、15、30

#### 数据示例

```
id: 1
user_id: oKXgA2f3rTVyibzgiX-PEfmXxmUc
daily_reminder_enabled: true
daily_reminder_time: 08:00
pre_schedule_reminder_enabled: true
pre_schedule_reminder_minutes: 10
timezone: Asia/Shanghai
```

---

## 3. 数据关系图

### 3.1 表关系

```
┌────────────────────────────────────────────────────────────────┐
│                         微信用户                                │
│                    (OpenID: oKXgA2f3...)                       │
└────────────────────────────────────────────────────────────────┘
                    │                           │
                    │ user_id                   │ user_id
                    ▼                           ▼
    ┌───────────────────────────┐   ┌───────────────────────────┐
    │        schedules          │   │      user_settings        │
    │        (日程表)            │   │      (用户设置)            │
    ├───────────────────────────┤   ├───────────────────────────┤
    │ id                        │   │ id                        │
    │ user_id ◄─────────────────┼───┼─► user_id                 │
    │ title                     │   │ daily_reminder_enabled    │
    │ description               │   │ daily_reminder_time       │
    │ scheduled_time            │   │ pre_schedule_..._enabled  │
    │ status                    │   │ pre_schedule_..._minutes  │
    │ ...                       │   │ ...                       │
    └───────────────────────────┘   └───────────────────────────┘
```

### 3.2 关系说明

- **一对一关系**：每个用户对应一条 user_settings 记录
- **一对多关系**：每个用户可以有多条 schedules 记录（多个日程）
- **数据隔离**：通过 user_id 字段，不同用户的数据互不干扰

---

## 4. 常用查询示例

### 4.1 查询用户的所有日程

```sql
SELECT * FROM schedules
WHERE user_id = '用户的OpenID'
AND status = 'active'
ORDER BY scheduled_time;
```

### 4.2 查询用户今天的日程

```sql
SELECT * FROM schedules
WHERE user_id = '用户的OpenID'
AND date(scheduled_time) = date('now')
AND status = 'active';
```

### 4.3 查询用户的提醒设置

```sql
SELECT * FROM user_settings
WHERE user_id = '用户的OpenID';
```

### 4.4 统计用户的日程数量

```sql
SELECT user_id, COUNT(*) as schedule_count
FROM schedules
WHERE status = 'active'
GROUP BY user_id;
```

---

## 5. 数据流转示例

### 5.1 用户添加日程的流程

```
用户发送: "添加日程，明天下午三点开会"
    │
    ▼
┌─────────────────────────────────┐
│  1. 获取用户的 OpenID           │
│     user_id = oKXgA2f3...       │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  2. AI 解析日程信息             │
│     title = "开会"              │
│     time = "明天下午3点"        │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  3. 时间解析器转换为具体时间     │
│     scheduled_time =            │
│     2026-02-14 15:00:00         │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  4. 写入数据库                  │
│  INSERT INTO schedules (        │
│    user_id,                     │
│    title,                       │
│    scheduled_time,              │
│    status                       │
│  ) VALUES (...)                 │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  5. 返回成功消息给用户          │
└─────────────────────────────────┘
```

### 5.2 提醒服务查询日程的流程

```
定时任务触发（每分钟）
    │
    ▼
┌─────────────────────────────────┐
│  1. 查询即将开始的日程          │
│  SELECT * FROM schedules        │
│  WHERE status = 'active'        │
│  AND scheduled_time BETWEEN     │
│    NOW() AND NOW() + 10分钟     │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  2. 遍历每个日程                │
│  - 获取 user_id                 │
│  - 检查用户设置是否开启提醒      │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  3. 发送微信提醒消息            │
│  "您有一个日程即将开始：        │
│   开会 - 15:00"                 │
└─────────────────────────────────┘
```

---

## 6. 数据库维护

### 6.1 备份数据库

```bash
# 复制数据库文件即可
cp data/wechat.db data/wechat_backup_$(date +%Y%m%d).db
```

### 6.2 清理已完成的旧日程

```sql
-- 删除30天前已完成的日程
DELETE FROM schedules
WHERE status = 'completed'
AND completed_at < date('now', '-30 days');
```

### 6.3 查看数据库大小

```bash
ls -lh data/wechat.db
```

---

## 7. 常见问题

### Q1: 用户数据会丢失吗？

不会。SQLite 数据库会将数据持久化存储在文件中，服务器重启后数据仍然存在。

### Q2: 多个用户同时使用会有问题吗？

不会。每个操作都是独立的事务，SQLite 会自动处理并发问题。

### Q3: 数据库文件可以移动吗？

可以。只需将 `wechat.db` 文件复制到新位置，并更新配置文件中的路径即可。

### Q4: 如何查看数据库内容？

可以使用工具：
- **命令行**: `sqlite3 wechat.db`
- **图形界面**: DB Browser for SQLite（免费）
- **VS Code 插件**: SQLite Viewer

---

## 8. 总结

本项目的数据库设计简洁高效：

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| schedules | 存储日程 | user_id, title, scheduled_time |
| user_settings | 存储用户设置 | user_id, daily_reminder_time |

通过 `user_id` 字段实现多用户数据隔离，确保每个用户只能访问自己的数据。
