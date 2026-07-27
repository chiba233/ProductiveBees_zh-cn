# 安全政策 / Security Policy

## 报告安全问题 / Reporting

这个 mod 里有**可执行代码**（一层 tooltip 显示层），所以它的安全面比纯资源包大。
如果你发现下面这类问题：

- mod 里出现了不该有的行为——联网、读写存档、改配方、发网络包
  （它**只应该**改 tooltip 上的字，别的什么都不做）；
- 构建脚本（`scripts/build.py`）存在可被利用的行为，例如哈希校验能被绕过、
  能被诱导去下别的东西；
- 发布的 jar 与本仓库这份源码对不上；

请**不要**公开发 Issue，直接发邮件到 **qwq@qwwq.org**，
标题注明 `[SECURITY] ProductiveBees_zh-cn`。会在 72 小时内回复。

If you find a security issue — the mod doing anything beyond rewriting tooltip
text (network access, save data, recipe changes), a way to bypass the hash
checks in `scripts/build.py`, or a published jar that does not match this
source — please do **not** open a public issue. Email **qwq@qwwq.org** with
subject `[SECURITY] ProductiveBees_zh-cn`. You will get a response within
72 hours.

## 这个 mod 做什么、不做什么

| | |
|---|---|
| 做 | 监听 `ItemTooltipEvent`，把资源蜜蜂物品 tooltip 里的蜂名换成中文；提供 lang 与导览书资源 |
| 不做 | 不注册任何方块 / 物品 / 实体，不改配方，不发网络包，不读写存档，不联网 |

`displayTest="IGNORE_ALL_VERSION"`，服务端没有它也照常进服；它是纯客户端显示层。

## 供应链

发布的 jar 从这份源码构建，所有外部输入都按字节钉死在 `SOURCE.lock` 里：

| 输入 | 锚点 |
|---|---|
| 译文与生成器（atm10-zh-cn） | git commit |
| 资源蜜蜂模组 jar | sha256 + CurseForge fileID（fileID 不可变，重传会换新 ID） |
| Gradle 发行版 | sha256 |
| NeoForge / ModDevGradle | 版本号 |

任何一项对不上，构建当场失败，不会「凑合出个包」。

仓库里**不放任何二进制**——包括 `gradle-wrapper.jar`，它是现下现核的。
