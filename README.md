# 资源蜜蜂 简体中文汉化

[Productive Bees](https://www.curseforge.com/minecraft/mc-mods/productive-bees) 的
**全量**简体中文汉化。**一个 jar，装完就是全部**——不用再装资源包，也不用往
`kubejs/` 里放脚本。

丢进 `mods/`，完事。

## 翻了什么

| | |
|---|---|
| 物品 / 方块 / 蜜蜂 / 界面 / 进度 | **1118 / 1118** 条（100%） |
| 内置导览书《蜜蜂大书》 | **81 / 81** 个页面文件（100%） |
| 基因样本 tooltip 里的**蜂种名** | **467** 个蜂种 |

最后那一行是这个东西非得做成 mod 的唯一理由。模组是这么拼它的：

```java
Component.translatable("productivebees.information.attribute.type", value)
//                                                                  ↑ 裸 String，运行期数据
```

`value` 从物品的 data component 里读出来，**不过任何 lang 查表**。资源包碰不到它；
改字节码常量池的工具（VaultPatcher 之流）也碰不到，因为那个串根本不在常量池里。
只能在 `ItemTooltipEvent` 上拦下来改——那就得有代码，那就得是 mod。

基因的各项**属性**（产量 / 耐力 / 脾气 / 习性 / 耐候 / 生命）和蜂笼上的
「类型：蜂巢型 / 独居型」走的是正经 lang 键，jar 里的资源已经覆盖。

## 支持范围

对着 `productivebees-1.21.1-13.13.5.jar` 逐条核过：**Minecraft 1.21.1 / NeoForge**。

| 目标 | 状态 |
|---|---|
| NeoForge 1.21.x | ✅ 已发布，lang 与导览书 100% |
| Forge / NeoForge 1.20.1 | 译文覆盖 99.8%，尚未出包 |
| Forge 1.19.2 / 1.18.2 | 译文覆盖 ~92.6%，缺的主要是各种木头蜂箱 |
| Forge 1.16.5 | 译文覆盖 65.8%，缺 255 条 |
| Fabric | **不存在**——资源蜜蜂本体从来没有 Fabric 版 |

一个 jar 跨不了这么多版本：1.16 跑 Java 8、1.17+ 跑 Java 17、1.20.5+ 跑 Java 21，
字节码版本就不兼容；Forge 与 NeoForge 的事件类也不是同一个包。所以每个目标各出一个
jar，各自对着那一版的模组 jar 验过覆盖率才发——**不到 100% 不出包**。
「装上去只翻了一半」比没翻还糟：玩家不会来报，只会觉得这包很烂。

## 它不做什么

只改 tooltip 上的字。不注册方块物品、不动配方、不发网络包、不碰存档。
`displayTest="IGNORE_ALL_VERSION"`，服务端没有它也照样进服。

## 译文放在哪 / 怎么提改进

译文**不在这个仓库**，在
[chiba233/atm10-zh-cn](https://github.com/chiba233/atm10-zh-cn)：

    src/pack/assets/productivebees/lang/zh_cn.json      语言文件
    src/books/assets/productivebees/**.json             导览书的「原文 → 译文」映射

这个仓库只负责**把它单独打成 mod**，本身不存任何一份译文副本，也不存 Gradle
wrapper 之类的二进制——上游按 commit 钉、模组 jar 按 sha256 钉、Gradle 发行版按
sha256 钉，全写在 `SOURCE.lock` 里。

为什么这么分：这份汉化本来就是
[All the Mods 10 汉化补丁「绿油油版」](https://github.com/chiba233/atm10-zh-cn)
的一部分。两边各存一份必然漂移，最后同一只蜂在整合包里叫一个名、在这里叫另一个名。

顺带一提，ATM10 整合包**不用**这个 mod——那边走 KubeJS 显示层，本来就装了 KubeJS，
更合适。这个 mod 是给其他整合包用的。两者互补。

**译名有问题、漏翻、错别字**：去上游仓库开 issue 或提 PR，改一次两边一起好。
**打包 / 安装 / 版本适配**：在这个仓库开 issue。

## 自己构建

```bash
python3 scripts/build.py r12
```

拉上游、核 jar、摊资源、编译、**对着打好的 jar 跑一遍译名自测**，产物在 `dist/`。

## 授权

GPL-3.0-or-later。Copyright (C) 2026 星野夢華 (Hoshino Yumeka)。

Productive Bees 本体由 jdkdigital 等作者开发，与本汉化无关；这里只提供中文资源与
一层显示层代码。
