// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// 验「整合包自己加的蜂能不能从玩家装的模组里现学出名字」。
//
// 输入是一份 JSON：
//   { "lang": {翻译键: 当前显示文本},        ← 模拟玩家那份语言表
//     "expect": {翻译键: 期望的中文} }        ← 从同一批模组的官方中文推出来的真值
// 真值不是我写的，是构造夹具时从模组自带中文里取的，见 scripts/addon_probe.py。

import cn.hoshino.pbzh.AddonNames;

import com.google.gson.Gson;
import com.google.gson.JsonObject;

import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;

public final class TestAddonNames {

    public static void main(String[] args) throws Exception {
        JsonObject doc;
        try (InputStreamReader r = new InputStreamReader(
                Files.newInputStream(Paths.get(args[0])), StandardCharsets.UTF_8)) {
            doc = new Gson().fromJson(r, JsonObject.class);
        }
        Map<String, String> lang = toMap(doc.getAsJsonObject("lang"));
        Map<String, String> expect = toMap(doc.getAsJsonObject("expect"));

        Map<String, String> got = AddonNames.compose(lang);

        // forbid：这几条是**必须学不出**的（译法有歧义、样本不足、已经是中文）。
        // 学错比学不出严重得多，所以这一项一旦破就直接失败。
        int forbidden = 0;
        if (doc.has("forbid")) {
            for (com.google.gson.JsonElement el : doc.getAsJsonArray("forbid")) {
                String k = el.getAsString();
                if (got.containsKey(k)) {
                    System.out.printf("  ❌ 不该学出来却学了 %-46s 实得 %s%n", k, got.get(k));
                    forbidden++;
                }
            }
            System.out.printf("必须学不出的 %d 条：%s%n", doc.getAsJsonArray("forbid").size(),
                    forbidden == 0 ? "一条都没越界" : forbidden + " 条越界");
        }
        if (forbidden > 0) {
            System.exit(1);
        }

        int ok = 0;
        int wrong = 0;
        int missed = 0;
        StringBuilder bad = new StringBuilder();
        for (Map.Entry<String, String> e : expect.entrySet()) {
            String g = got.get(e.getKey());
            if (g == null) {
                missed++;
                if (missed <= 8) {
                    bad.append(String.format("  没学出来 %-52s 期望 %s%n",
                            e.getKey(), e.getValue()));
                }
            } else if (g.equals(e.getValue())) {
                ok++;
            } else {
                wrong++;
                if (wrong <= 8) {
                    bad.append(String.format("  学错了   %-52s 期望 %s 实得 %s%n",
                            e.getKey(), e.getValue(), g));
                }
            }
        }
        // 没在期望表里、却被我们补出来的：这些是额外收益，但也要看看有没有乱补
        int extra = 0;
        for (String k : got.keySet()) {
            if (!expect.containsKey(k)) {
                extra++;
            }
        }

        System.out.printf("待补的整合包蜂键 %d 条%n", expect.size());
        System.out.printf("  学对 %d 条（%.1f%%）  学错 %d 条  学不出 %d 条%n",
                ok, ok * 100.0 / Math.max(1, expect.size()), wrong, missed);
        System.out.printf("  另外还补出 %d 条不在期望表里的%n", extra);
        if (bad.length() > 0) {
            System.out.print(bad);
        }
        // 学错比学不出严重得多：学不出只是显示英文，学错是张冠李戴
        if (wrong > 0) {
            System.out.println("❌ 有学错的，不合格");
            System.exit(1);
        }
        System.out.println("✅ 没有一条学错");
    }

    private static Map<String, String> toMap(JsonObject o) {
        Map<String, String> m = new LinkedHashMap<>();
        if (o != null) {
            o.entrySet().forEach(e -> m.put(e.getKey(), e.getValue().getAsString()));
        }
        return m;
    }
}
