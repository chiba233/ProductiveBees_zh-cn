// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// 对着**打好的那个 jar** 跑：加载里面真的 BeeNames.class，读里面真的 bees.json。
//
// 样本从那张表里现取，不写死某一只蜂——每个平台目标的蜂名表都不一样，
// 写死就只能过一个目标。测的是**机制**：该翻的翻了、不该碰的没碰。
//
// 跑法（scripts/build.py 会自动跑）:
//   javac -d <out> TestTranslate.java
//   java -cp <out>:<mod jar>:<gson jar> TestTranslate
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStreamReader;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Map;

public class TestTranslate {
    static int failed = 0;
    static Method translate;

    static void check(String label, String in, String want) throws Exception {
        String got = (String) translate.invoke(null, in);
        boolean ok = got.equals(want);
        if (!ok) {
            failed++;
        }
        System.out.println((ok ? "  ok  " : "  ❌  ") + label + "  " + in);
        if (!ok) {
            System.out.println("      期望 " + want);
            System.out.println("      实得 " + got);
        }
    }

    static Map.Entry<String, String> first(JsonObject o) {
        for (Map.Entry<String, com.google.gson.JsonElement> e : o.entrySet()) {
            return Map.entry(e.getKey(), e.getValue().getAsString());
        }
        throw new IllegalStateException("表是空的");
    }

    public static void main(String[] args) throws Exception {
        Class<?> c = Class.forName("cn.hoshino.pbzh.BeeNames");
        translate = c.getDeclaredMethod("translate", String.class);
        translate.setAccessible(true);

        JsonObject tables = JsonParser.parseReader(new InputStreamReader(
                c.getResourceAsStream("/pbzh/bees.json"), StandardCharsets.UTF_8))
                .getAsJsonObject();

        // 这个 mod 存在的唯一理由：基因样本 tooltip 里那行运行期拼出来的蜂种名
        Map.Entry<String, String> type = first(tables.getAsJsonObject("type2zh"));
        check("类型行", "类型: " + type.getKey() + " (100%)",
                "类型: " + type.getValue() + " (100%)");
        check("类型行(英文标签)", "Type: " + type.getKey() + " (50%)",
                "Type: " + type.getValue() + " (50%)");

        // 原始 ID 形态
        Map.Entry<String, String> id = first(tables.getAsJsonObject("id2zh"));
        check("原始ID", "productivebees:" + id.getKey(), id.getValue());
        check("原始ID(_bee后缀)", "productivebees:" + id.getKey() + "_bee", id.getValue());

        // 不该动的：没有 (N%) 就不是类型行，绝不做贪婪替换
        check("非类型行不碰", "类型: " + type.getKey(), "类型: " + type.getKey());
        // 表里没有的串原样透传
        check("陌生串透传", "Ancient Beekeeper Zzz", "Ancient Beekeeper Zzz");
        check("空串", "", "");

        System.out.println(failed == 0 ? "✅ 全部通过" : "❌ " + failed + " 项没过");
        if (failed > 0) {
            System.exit(1);
        }
    }
}
