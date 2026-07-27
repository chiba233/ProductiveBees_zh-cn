// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化（独立发布）
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// 对着**打好的那个 jar** 跑：加载里面真的 BeeNames.class，读里面真的 bees.json，
// 拿真实的 tooltip 文本比对。不是对着源码跑，也不是对着另一份表跑。
//
// 跑法（scripts/build.py 会自动跑）:
//   javac -d <out> TestTranslate.java
//   java -cp <out>:<mod jar>:<gson jar> TestTranslate
import java.lang.reflect.Method;

public class TestTranslate {
    static int failed = 0;

    static void check(Method m, String in, String want) throws Exception {
        String got = (String) m.invoke(null, in);
        boolean ok = got.equals(want);
        if (!ok) {
            failed++;
        }
        System.out.println((ok ? "  ok  " : "  ❌  ") + in);
        if (!ok) {
            System.out.println("      期望 " + want);
            System.out.println("      实得 " + got);
        }
    }

    public static void main(String[] args) throws Exception {
        Class<?> c = Class.forName("cn.hoshino.pbzh.BeeNames");
        Method m = c.getDeclaredMethod("translate", String.class);
        m.setAccessible(true);

        // 这个 mod 存在的唯一理由：基因样本 tooltip 里那行运行期拼出来的蜂种名
        check(m, "类型: Kamikaz (100%)", "类型: “神风特攻队”蜜蜂 (100%)");
        check(m, "Type: Kamikaz (100%)", "Type: “神风特攻队”蜜蜂 (100%)");
        check(m, "类型: Diamond (50%)", "类型: 钻石蜜蜂 (50%)");

        // 原始 ID 形态
        check(m, "productivebees:diamond_bee", "钻石蜜蜂");

        // 不该动的：没有 (N%) 的整段不匹配，绝不做贪婪替换
        check(m, "类型: Kamikaz", "类型: Kamikaz");
        // 玩家自己起的名字、不相干的英文，一律不碰
        check(m, "Ancient Beekeeper", "Ancient Beekeeper");
        check(m, "", "");

        // 歧义英文名必须**保持英文**：两只蜂都叫 Amber Bee，宁可不翻也不能张冠李戴
        check(m, "Amber Bee", "Amber Bee");

        System.out.println(failed == 0 ? "✅ 全部通过" : "❌ " + failed + " 项没过");
        if (failed > 0) {
            System.exit(1);
        }
    }
}
