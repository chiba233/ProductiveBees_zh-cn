<!--
改译文请去上游仓库：https://github.com/chiba233/atm10-zh-cn
译文不在这个仓库，在这里改会被漂移掉。
-->

## 改了什么

## 为什么

<!-- 这个仓库的注释与文档要求写「为什么」，不是「改了什么」——改了什么 diff 里能看见。 -->

## 自查

- [ ] `python3 scripts/build.py dev` 能跑通，三道闸都过了
      （覆盖率 100% / 占位符与导览书结构 / 对着打好的 jar 跑 TestTranslate）
- [ ] 没有把生成物加进 git：`mod/src/main/resources/`、`build/`、`dist/`、
      `upstream/`、Gradle 缓存都不入库
- [ ] 没有引入任何二进制（包括 `gradle-wrapper.jar`）
- [ ] Java 里没有写死任何中文——译名一律来自上游生成的 `pbzh/bees.json`
- [ ] 改了外部依赖的话，`SOURCE.lock` 里的哈希一并更新了
