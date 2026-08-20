<p align="center">
  <img src="src/logo.png" width="160" height="160" alt="资源蜜蜂 简体中文汉化">
</p>

# 资源蜜蜂 简体中文汉化

[Productive Bees](https://www.curseforge.com/minecraft/mc-mods/productivebees) 的中文
mod。**放进 `mods/` 即可**，不需要资源包，也不需要改配置。

只改显示层：不注册方块物品、不动配方、不发网络包、不碰存档。服务端没有本 mod
也能正常进服。

## 服务器要不要也装

**1.21 / 1.21.1 请也放一份到服务端的 `mods/`。** 放了之后蜂笼里的蜜蜂名字才是中文，
**以前抓的那些也会自动改回来**。其余版本服务端装了没有这项功能。

蜂名不是翻译键：`BeeCage` 在**捕捉的那一刻**就把显示名解析成一段普通文字写进了
物品里，谁抓的就按谁的语言表解析。服务端没有中文，写进去的就是 `Dark Steel Bee`，
之后客户端再怎么翻都够不着它。所以这件事只能在服务端做。

改名有三道闸，玩家自己起的名字一个都不碰：

- 名字里已经有汉字的，不动
- 当前名字不在「模组自己生成的英文名」表里的，不动——**用命名牌起的名字长这样**
- 改成什么由蜂的 **id** 决定，不拿英文名反查

服务端不装也照样能进服，只是蜂笼名保持英文。

## 下载

去 [Releases](../../releases)，按你的 Minecraft 版本和加载器选文件：

    productivebees-zh_cn-<版本>-mc<Minecraft版本>-<加载器>.jar

## 支持哪些版本

<!-- 支持矩阵开始 · 由 scripts/readme.py 生成，勿手改 -->

| Minecraft | 加载器 | 词条 | 导览书 | 状态 |
|---|---|---|---|---|
| 1.21.1 | NeoForge | 1145 / 1145 | 81 / 81 | ✅ 可用 |
| 1.21 | NeoForge | 1103 / 1103 | 81 / 81 | ✅ 可用 |
| 1.20.1 | NeoForge | 1036 / 1036 | 81 / 81 | ✅ 可用 |
| 1.20.1 | Forge | 1036 / 1036 | 81 / 81 | ✅ 可用 |
| 1.20 | NeoForge | 907 / 907 | 92 / 92 | ✅ 可用 |
| 1.20 | Forge | 907 / 907 | 92 / 92 | ✅ 可用 |
| 1.19.4 | Forge | 626 / 626 | 92 / 92 | ✅ 可用 |
| 1.19.3 | Forge | 614 / 614 | 92 / 92 | ✅ 可用 |
| 1.19.2 | Forge | 627 / 627 | 92 / 92 | ✅ 可用 |
| 1.19.1 | Forge | 583 / 583 | 89 / 89 | ✅ 可用 |
| 1.19 | Forge | 575 / 575 | 89 / 89 | ✅ 可用 |
| 1.18.2 | Forge | 610 / 610 | 92 / 92 | ✅ 可用 |
| 1.18.1 | Forge | 561 / 561 | 89 / 89 | ✅ 可用 |
| 1.18 | Forge | 747 / 747 | 86 / 86 | ✅ 可用 |
| 1.17.1 | Forge | 740 / 740 | 86 / 86 | ✅ 可用 |
| 1.16.5 | Forge | 745 / 745 | 86 / 86 | ✅ 可用 |
| 1.16.4 | Forge | 553 / 553 | 84 / 84 | ✅ 可用 |
| 1.16.3 | Forge | 553 / 553 | 84 / 84 | ✅ 可用 |
| 1.16.1 | Forge | 557 / 557 | 26 / 26 | ✅ 可用 |
| 1.15.2 | Forge | 537 / 537 | 31 / 31 | ✅ 可用 |

<!-- 支持矩阵结束 -->

「已汉化条目」为该版模组语言条目的翻译数量。缺几条，游戏内就会有几处显示英文。

## 覆盖哪些整合包

<!-- 覆盖范围开始 · 由 scripts/readme.py 生成，勿手改 -->

已逐个翻过 **71824** 个整合包与模组（CurseForge 2490 个、Modrinth 整合包 18294 个、Modrinth 模组 51403 个；363 个取不到文件）。其中 **68** 个自带蜂名——它们用数据包加了自己的蜂，名字不在模组本体里。这些名字**也在本汉化里**：

| 整合包 | 自定义条目 | 下载量 |
|---|---:|---:|
| MineColonies - Cobblemon Conquest | 32 | 27,460 |
| MineColonies - Create & Conquer | 16 | 143,689 |
| TechEv \|\| Discovery | 16 | 7,977 |
| MOTCraft server | 16 | 1,196 |
| Nightwing Diamond | 15 | 170 |
| MartinClan2026 | 15 | 120 |
| Dungeons, Dragons and Space Shuttles 2 | 14 | 58,090 |
| ATM : All Tech Mods | 14 | 13,918 |
| Aoura MC | 13 | 243 |
| Mordant Minds | 12 | 142 |
| Psi: Tweaks and Additions | 11 | 2,498 |
| Phoenix Forge Technologies | 11 | 1,586 |
| WithTheCat (Second Edition) | 10 | 511 |
| Bee Proud | 9 | 7,694 |
| Ender IO: Evolution | 8 | 9,564 |
| DivineRPG | 6 | 510,028 |
| DivineRPG: Compatability | 6 | 142,039 |
| DivineRPG Compatability | 6 | 12,485 |
| Journey Through The Abyss | 6 | 5,897 |
| Bee Master | 6 | 897 |
| Sky Bees Reborn | 5 | 16,979 |
| Dungeons and Shuttles Evolution | 5 | 3,220 |
| Fated Curse | 5 | 708 |
| Civilization Isolaria | 5 | 96 |
| Cobblemon Add-on: Mega Showdown Ores | 4 | 11,158 |
| …另有 43 个 | | |

未列出的整合包同样适用：本汉化覆盖模组本体的全部词条，整合包自定义的蜂名是额外补充的一层。

<!-- 覆盖范围结束 -->

## 翻了什么

- 物品、方块、蜜蜂名、界面、进度
- 内置导览书《蜜蜂大书》全部页面
- **基因样本 / 蜜蜂小食 tooltip 里的蜂种名**（467 个蜂种）——
  这一行是运行期拼出来的，资源包翻不到，只有 mod 能翻

## 提问题

| | |
|---|---|
| 译名不对、漏翻、错别字 | [开 issue](../../issues/new/choose) |
| 装了之后崩溃 / 没生效 / 进不了服 | [开 issue](../../issues/new/choose) |
| 想要还没支持的版本 | [开 issue](../../issues/new/choose) |
| 蜜蜂本身的 bug（不产东西、配方不对） | [Productive Bees](https://github.com/jdkdigital/productive-bees/issues) |

## 致谢

**[十一月の风筝](https://space.bilibili.com/2041176282)**（测试）

## 授权

按类别分别授权，详见 [LICENSE](LICENSE)：

| | |
|---|---|
| 代码（`scripts/`、`mod/`、CI） | GPL-3.0-or-later · (C) 2026 星野夢華 |
| 译文（`src/lang`、`src/books`） | (C) 2026 星野夢華，保留一切权利 |
| Productive Bees 本体 | (C) [JDKDigital](https://www.curseforge.com/minecraft/mc-mods/productivebees)，**All Rights Reserved** |

本仓库**不含任何上游文件**——不放 jar、不放上游语言文件、不放上游导览书，
只记「英文原文 → 中文译文」的对应表。

**分发已获作者答复。** 2026-07-30，Productive Bees 作者 LobsterJonn 在 CurseForge
私信中答复：翻译类的发布不需要额外许可；他欢迎以 PR 形式并入译文，但只能为
1.21.1 与 26.1.2 发布，其余版本仍需由本项目自行建立 CurseForge 项目。

本汉化与 JDKDigital 无隶属关系，也未获其背书。
