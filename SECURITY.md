# 安全政策

发现问题请发邮件到 **qwq@qwwq.org**，标题带 `[SECURITY] ProductiveBees_zh-cn`，
不要公开发 issue。72 小时内回复。

值得报的：

- mod 做了改 tooltip 文字之外的事——联网、读写存档、改配方、发网络包
- 发布的 jar 与本仓库源码对不上
- `scripts/build.py` 的哈希校验能被绕过

## 这个 mod 会做什么

只有一件事：监听 `ItemTooltipEvent`，把资源蜜蜂物品 tooltip 里的蜂名换成中文，
另外提供语言文件与导览书资源。

不注册任何方块 / 物品 / 实体，不改配方，不发网络包，不读写存档，不联网。
纯客户端，服务端没有它照样进服。

## 构建的外部输入

| 输入 | 校验 |
|---|---|
| 资源蜜蜂模组 jar | sha256 + CurseForge fileID（见 `versions/targets.json`） |
| Gradle 发行版 | sha256（见 `deps.lock.json`） |

对不上就构建失败。仓库里不放任何二进制。
