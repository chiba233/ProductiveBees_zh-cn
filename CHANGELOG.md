# Changelog

版本号是标准 semver：`x.y.z` / `x.y.z-beta.N` / `x.y.z-rc.N`。
它要写进 `neoforge.mods.toml` 的 `version`，加载器按 Maven 语义比较大小，
所以不能用别的编号方式。

Release 说明由 CI 从这里按 `## <版本>` **整串精确比对**取出——
别用前缀匹配，`## 1.0` 会把 `## 1.0.1` 也匹上。

## 1.0.0-rc.1

首个可发布版本。

### 一个 jar 装完就是全部汉化

不用再装资源包，也不用往 `kubejs/` 里放脚本。丢进 `mods/`，完事。

| | |
|---|---|
| 物品 / 方块 / 蜜蜂 / 界面 / 进度 | 1118 / 1118 条（对着 1.21.1 那一版核的） |
| 内置导览书《蜜蜂大书》 | 81 / 81 个页面文件 |
| 基因样本 tooltip 里的**蜂种名** | 467 个蜂种 |

最后那一行是这东西非得做成 mod 的唯一理由。模组是这么拼它的：

```java
Component.translatable("productivebees.information.attribute.type", value)
//                                                                  ↑ 裸 String，运行期数据
```

`value` 从物品的 data component 里读出来，不过任何 lang 查表。资源包碰不到它；
改字节码常量池的工具也碰不到，因为那个串根本不在常量池里。只能在
`ItemTooltipEvent` 上拦——那就得有代码，那就得是 mod。

### 全版本矩阵

把 CurseForge 上这个模组的文件列表整个翻了一遍，按 (MC 版本, 加载器) 取最新的一份
逐个下下来，抽 `en_us` 的 key 与导览书清单算并集：

- 20 个平台目标：Forge 1.15.2–1.20.1 / NeoForge 1.20–1.21.1
- **Fabric 不存在**：CurseForge 的 gameVersions 与 Modrinth 的 loaders 两个独立来源
  都只有 forge / neoforge。不做空 jar。
- 全历史 lang key 并集 1504 个

一次 build 出全部平台，**全部 jar 共用 `src/` 里同一份数据源**，不会为哪个整合包
单独编一个。各平台之间只差字节码目标（1.16 跑 Java 8、1.17–1.20.4 跑 17、
1.20.5+ 跑 21）与加载器元数据。

### 三道闸，过不了不出包

| 闸 | 查什么 |
|---|---|
| 覆盖率 | 目标 jar 的 `en_us` 每个键、导览书每个页面文件都得有中文 |
| 占位符与结构 | 译文占位符集合必须 ⊆ 英文的；`%s` 不许降级；结尾不许裸 `%`；导览书中文版 JSON 结构必须与英文版逐键一致（Patchouli 按结构读，对不上那一页**静默不显示**） |
| 自测 | 对着**打好的那个 jar** 跑 `TestTranslate`——真字节码、真打进去的表、真 tooltip 文本 |
