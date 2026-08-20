# 参与贡献

## 改译名

译文在 `src/lang/zh_cn.json`，键名就是模组的语言键。导览书在 `src/books/`，
存的是「英文原文 → 中文」的映射，构建时套到模组自带那份 JSON 上。

改完提交 PR 即可，CI 会跑全套检查。

### 「玄钢蜜蜂蜜脾」这种重复，是已知的、不修

没有专属蜜脾条目的蜂（约 522 只），蜜脾名由模组现拼，`Honeycomb#getName` 的做法是
拿蜂名去掉结尾的 ` Bee` 再套 `item.productivebees.honeycomb_configurable`：

    Dark Steel Bee  →  去掉 " Bee"  →  Dark Steel  →  "%s Comb"  →  Dark Steel Comb
    玄钢蜜蜂         →  去不掉        →  玄钢蜜蜂     →  "%s蜜脾"    →  玄钢蜜蜂蜜脾

中文构词方向和英文相反，这个字符串拼法从根上就接不住。**要真修只能上 Mixin 改
`ItemStack#getHoverName`**——只改 `ItemTooltipEvent` 的话，JEI 物品列表和容器标题
那两条渲染路径仍然是重复的名字，等于修一半。

权衡下来不修：名字虽然啰嗦但意思不错，JEI 里照样搜得到。别再为它开 Mixin，
也别把 `%s蜜脾` 改成 `%s`——那会让蜜脾显示成「玄钢蜜蜂」，比啰嗦更糟。

### 一个名字该在服务端烤进数据，还是在客户端换显示

两条判据，**顺序不能反**：

    1. 改这个字段会不会坏功能？
         会   → 绝不动数据，只能在显示层换
    2. 这个字段有几个消费者？
         多个 → 必须改数据本身（只改一个消费者就是半截货）
         一个 → 显示层足够

**蜂笼 `custom_data.name`**：不坏功能 + 消费者一大堆（悬停 tooltip、快捷栏浮动名、
JEI、Jade、搜索、别的 mod 的显示）。客户端只挂得上其中一个（`ItemTooltipEvent`），
改一个剩下的还是英文。所以**必须在服务端把数据本身改掉**，所有消费者读的是同一个
值，才会同时正确。这是「单一真源」在运行期的形态：客户端替换等于在真源之外又糊了
第二个真源，正是这个仓库禁的东西。

**基因样本的 `value`**：它同样是权威数据，但**是功能数据**——育种、基因索引机靠它
判断这份基因属于哪种蜂，改了机制就坏了。而它只有一个消费者（物品 tooltip 那一行），
所以显示层替换既够用又不会留半截。

走反任何一条都出事：蜂笼走客户端 = 半截货（P0）；基因走服务端 = 毁存档。

## 补还没翻的版本

README 的支持矩阵里带「差 N 条」的，就是待办。列出某个版本缺哪些键：

```bash
python3 scripts/versions.py gap
```

老版本缺的多为各种木头的蜂箱（`block.productivebees.advanced_<木头>_beehive`），
成规律，可以批量补。

## 自己构建

要 Python 3 与 JDK 8 / 17 / 21。

```bash
python3 scripts/build.py 1.0.0                    # 出全部平台
python3 scripts/build.py 1.0.0 1.21.1-neoforge    # 只出一个
```

产物在 `dist/`。版本号必须是 `x.y.z` / `x.y.z-beta.N` / `x.y.z-rc.N`。

## 加新的 Minecraft 版本

```bash
python3 scripts/versions.py scan
```

重新扫模组在 CurseForge 上的全部发行，更新 `versions/targets.json`
与 `versions/keys.json`，然后 `python3 scripts/readme.py` 重写支持矩阵。

## 检查

出包前有三道检查，任一不过就不出包：

| | |
|---|---|
| 覆盖率 | 目标版本的每个语言条目、每个导览书页面都必须有中文 |
| 格式 | 占位符不能比英文多、`%s` 不能降级成 `%d`、结尾不能是裸 `%`；导览书中文版的 JSON 结构要和英文版一致 |
| 自测 | 对着打好的 jar 跑 `mod/test/TestTranslate.java`，验蜂名替换的实际行为 |

## 目录

```
src/lang/zh_cn.json     译文
src/books/              导览书映射
scripts/                构建与检查
mod/                    Gradle 工程与 Java 源码
versions/               各版本的目标信息与语言键清单
```

`mod/src/main/resources/`、`build/`、`dist/` 都是构建时生成的，不入库。

## 授权

提交即表示同意以 GPL-3.0-or-later 授权。
