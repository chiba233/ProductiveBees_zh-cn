# 参与进来

先说清楚一件事，能省掉大部分误会：

> **译文不在这个仓库。** 这里只负责把它打成 mod。

译文与生成器都在
[chiba233/atm10-zh-cn](https://github.com/chiba233/atm10-zh-cn)：

    src/pack/assets/productivebees/lang/zh_cn.json      语言文件
    src/books/assets/productivebees/**.json             导览书的「原文 → 译文」映射

这么分是因为这份汉化本来就是 ATM10 汉化补丁的一部分。两边各存一份必然漂移，
最后同一只蜂在整合包里叫一个名、在这里叫另一个名。所以只留一份真源。

| 你想做的事 | 去哪 |
|---|---|
| 译名不对、漏翻、错别字、导览书内容 | **上游仓库**开 issue / 提 PR，改一次两边一起好 |
| 装了 mod 崩溃、tooltip 没生效、进不了服 | 这个仓库 |
| 适配别的 Minecraft 版本 / Forge | 这个仓库 |

## 仓库里有什么

入库的只有源与配置，一共十几个文件：

    SOURCE.lock     上游 commit、模组 jar sha256/fileID、Gradle 发行版 sha256、NeoForge 版本
    manifest.json   产出什么、覆盖率下限
    scripts/build.py  拉上游 → 核 jar → 摊资源 → 编译 → 自测
    scripts/pack.py   摊资源、核覆盖率与占位符、抠蜂名表
    mod/            Gradle 工程与 Java 源码

**不入库的**：译文（在上游）、Python 现摊出来的 `mod/src/main/resources/`、
Gradle 发行版与缓存、`gradle-wrapper.jar`（那是二进制）、产物 jar。

## 自己构建

要 Python 3 与 JDK 21（NeoForge 1.21.1 跑在 Java 21 上）。

```bash
python3 scripts/build.py r12
```

它会按 `SOURCE.lock` 把上游、模组 jar、Gradle 逐个下下来**并核哈希**，
然后摊资源、编译、跑自测，产物落在 `dist/`。

## 三道闸，过不了不出包

| 闸 | 查什么 |
|---|---|
| 覆盖率 | 目标 jar 的 `en_us` 每个键、导览书每个页面文件都得有中文，**不到 100% 不出包** |
| 占位符与结构 | 译文的占位符集合必须 ⊆ 英文的；`%s` 不许降级；结尾不许裸 `%`；导览书中文版的 JSON 结构必须与英文版逐键一致（Patchouli 按结构读，对不上那一页会**静默不显示**） |
| 自测 | 对着**打好的那个 jar** 跑 `TestTranslate`——真字节码、真打进去的表、真 tooltip 文本 |

「装上去只翻了一半」比没翻还糟：玩家不会来报，只会觉得这包很烂。所以宁可不出包。

## 代码怎么分层

```
BeeNames     纯逻辑，**一个 Minecraft 类型都不引用** → 能脱离游戏直接跑测试
TooltipHook  唯一碰 Minecraft/NeoForge 类型的地方，只做事件转接
```

译名表 `pbzh/bees.json` 由 Python 在构建时从上游生成后打进 jar，
**Java 里一个中文都不许写死**——写死就又变成两份译名。

## 加一个 Minecraft 版本

不是改代码，是先看数据：拿那一版的模组 jar 跑覆盖率。目前实测：

| 目标 | lang | 导览书 |
|---|---|---|
| 1.21.x NeoForge | 100% | 100% |
| 1.20.1 Forge + NeoForge | 99.8% | 100% |
| 1.19.2 / 1.18.2 Forge | ~92.6% | 88% |
| 1.16.5 Forge | 65.8% | 88.4% |
| Fabric | 不适用——**资源蜜蜂本体从来没有 Fabric 版** | — |

差的那些得先在**上游**把译文补齐，这边才出得了包。

一个 jar 跨不了 1.16→1.21：1.16 跑 Java 8、1.17+ 跑 Java 17、1.20.5+ 跑 Java 21，
字节码版本就不兼容；Forge 与 NeoForge 的事件类也不是同一个包。所以每个目标各出一个 jar。

## 授权

提交即表示同意以 GPL-3.0-or-later 授权。
