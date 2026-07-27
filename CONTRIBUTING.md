# 参与贡献

## 改译名

译文在 `src/lang/zh_cn.json`，键名就是模组的语言键。导览书在 `src/books/`，
存的是「英文原文 → 中文」的映射，构建时套到模组自带那份 JSON 上。

改完提 PR 就行，CI 会跑全套检查。

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

出包前会跑三道，过不了就不出：

| | |
|---|---|
| 覆盖率 | 目标版本的每个语言条目、每个导览书页面都得有中文 |
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
