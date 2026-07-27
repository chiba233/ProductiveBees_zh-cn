# 资源蜜蜂 简体中文汉化

[Productive Bees](https://www.curseforge.com/minecraft/mc-mods/productive-bees) 的
**全量**简体中文汉化：物品、方块、蜜蜂、界面、进度，**以及内置导览书《蜜蜂大书》的
全部页面**。

不绑定任何整合包，装了这个模组就能用。

## 装法（二选一，别两个都装）

| 形态 | 怎么装 | 适用 |
|---|---|---|
| `productivebees-zh_cn-<版本>-resourcepack.zip` | 丢进 `.minecraft/resourcepacks/`，游戏里「选项 → 资源包」启用 | 任何加载器、任何启动器 |
| `productivebees-zh_cn-<版本>.jar` | 丢进 `mods/`，自动生效，不用管资源包顺序 | 仅 NeoForge |

那个 `.jar` **里面没有一行 Java 代码**，只是资源——用的是 NeoForge 的 `lowcodefml`
加载器，就是给纯资源/数据模组用的。

去 [Releases](../../releases) 下载。

## 覆盖到什么程度

对着 `productivebees-1.21.1-13.13.5.jar`（Minecraft 1.21.1 / NeoForge）逐条核过：

| | |
|---|---|
| 语言键 | **1118 / 1118**（100%） |
| 导览书页面文件 | **81 / 81**（100%） |

覆盖率是**出包时现算的硬门控**：拿目标 jar 的 `en_us` 与导览书逐个点名，够不到
100% 直接不出包。「装上去只翻了一半」比没翻还糟——玩家不会来报，只会觉得这包很烂。

别的 Productive Bees 版本多半也能用（lang 键很稳），但只有上面这一份是**验过**的。

## 已知边界

- 蜜蜂 tooltip 里那句**动态类型行**（运行期拼出来的构词）不是 lang 键，独立包翻不到，
  保持英文。蜜蜂本身的名字是正经 lang 键，照常汉化。
- 只翻 `productivebees` 一个命名空间。ModularBees 等附属模组不在这个包里。

## 译文放在哪 / 怎么提改进

译文**不在这个仓库**，在
[chiba233/atm10-zh-cn](https://github.com/chiba233/atm10-zh-cn)：

    src/pack/assets/productivebees/lang/zh_cn.json      语言文件
    src/books/assets/productivebees/**.json             导览书的「原文 → 译文」映射

这个仓库只负责**把它单独打出来发布**，本身不存任何一份译文副本。

为什么这么分：这份汉化本来就是
[All the Mods 10 汉化补丁「绿油油版」](https://github.com/chiba233/atm10-zh-cn)
的一部分。两边各存一份的话必然漂移，最后同一只蜂在整合包里叫一个名、在这里叫另一个名。
所以只留一份真源，这边现摊现打。

**译名有问题、漏翻、错别字**：去上游仓库开 issue 或提 PR，改一次两边一起好。
**打包/安装/发布方面的问题**：在这个仓库开 issue。

## 授权

GPL-3.0-or-later。Copyright (C) 2026 星野夢華 (Hoshino Yumeka)。

Productive Bees 本体由 Nurdbot 等作者开发，与本汉化无关；这里只提供中文资源。
