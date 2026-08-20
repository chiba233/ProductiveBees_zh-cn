// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化（独立发布）
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 把资源蜜蜂 tooltip 里**运行期拼出来的蜂名**换成中文。
 *
 * <p>模组是这么拼那一行的：
 * <pre>Component.translatable("productivebees.information.attribute.type", value)</pre>
 * {@code value} 是从物品 data component 里读出来的裸 String，不过任何 lang 查表。
 * 资源包碰不到它，改常量池的工具（VaultPatcher 之流）也碰不到——那个串根本不在
 * 常量池里，是运行期数据。所以只能在这里拦。
 *
 * <p>这个类里**没有一个 Minecraft 类型**——事件胶水在 {@link TooltipHook}。
 * 分开是为了能脱离游戏直接跑测试：真逻辑全在这儿，测试拿打好的 jar 就能验。
 *
 * <p>译名表 {@code /pbzh/bees.json} 是构建时由 Python 从 {@code src/lang/zh_cn.json}
 * ——和词条同一份数据源——生成的，这个类里一个中文都不写死。
 *
 * <p>几条从整合包版继承下来的安全规矩，都是踩过才有的：
 * <ul>
 *   <li>歧义英文名（两只蜂都叫 Amber Bee）在**生成期**就剔掉了，宁可显示英文，
 *       也不能张冠李戴。</li>
 *   <li>类型行只做整段精确匹配（{@code 类型: X (100%)}），不做贪婪替换——
 *       半截替换（{@code Ter-蜜蜂-Nator}）比不翻更糟。</li>
 *   <li>英文名替换带词边界，防止 {@code Ancient Bee} 命中 {@code Ancient Beekeeper}。</li>
 *   <li>玩家用命名牌/铁砧起的名字不碰：这里只改 tooltip 的文本，
 *       而且只在整段能对上表的时候改。</li>
 * </ul>
 */
public final class BeeNames {
    private static final Map<String, String> ID2ZH = new LinkedHashMap<>();
    private static final Map<String, String> EN2ZH = new LinkedHashMap<>();
    private static final Map<String, String> TYPE2ZH = new LinkedHashMap<>();

    /** 原始 ID：productivebees:xxx（可带 _bee 后缀） */
    private static final Pattern RAW_ID = Pattern.compile("productivebees:([a-z0-9_]+)");
    /** 类型行：整段精确匹配，X 后面必须紧跟 (数字%) */
    private static final Pattern TYPE_LINE =
            Pattern.compile("(类型|Type)([:：]\\s*)([A-Za-z][A-Za-z' .-]*?)(\\s*\\(\\d+%\\))");
    /** 英文整名，长名优先 + 词边界；表为空时保持 null，跳过这一步 */
    private static final Pattern EN_NAMES;

    static {
        load();
        EN_NAMES = EN2ZH.isEmpty() ? null : Pattern.compile(
                "\\b(?:" + String.join("|", quotedLongestFirst(EN2ZH.keySet())) + ")(?![A-Za-z])");
    }

    private BeeNames() {
    }

    /**
     * 启动时报一声，把表的规模一并说出来。
     *
     * <p>不是装饰：**Forge 启动时根本不打印 mod 列表**（NeoForge 才打印），
     * 服主没有任何办法确认这个 mod 到底装上没有、表有没有打进 jar。有了这一行，
     * 「验证装对了没有」就有了第一条可自查的证据，服务端冒烟测试也有了判据。
     */
    static void hello(String where) {
        System.out.println("[productivebees_zh_cn] 已加载（" + where + "）：蜂名 "
                + ID2ZH.size() + " 条");
    }

    /** 「蜂 id → 中文名」，给 {@link BeeData} 改 NBT 用。表是构建时生成的。 */
    static Map<String, String> idTable() {
        return ID2ZH;
    }

    /**
     * 「英文整名 → 中文名」。给服务端那条改名路当**安全闸**用：只有当前这个名字
     * 确实是模组自己生成的英文名时才允许改写，玩家用命名牌起的名字一律不碰。
     *
     * <p>生成期剔掉的那几个歧义名（两只蜂都叫 Amber Bee）不在表里，于是那几只的
     * 蜂笼会保持英文——宁可少改，也不能把玩家的东西改坏。
     */
    static Map<String, String> enTable() {
        return EN2ZH;
    }

    private static List<String> quotedLongestFirst(Iterable<String> keys) {
        List<String> out = new ArrayList<>();
        for (String k : keys) {
            out.add(Pattern.quote(k));
        }
        // 长的排前面：正则的交替是最左匹配，短名在前会把长名截成两半
        out.sort(Collections.reverseOrder(java.util.Comparator.comparingInt(String::length)));
        return out;
    }

    private static void load() {
        try (InputStream in = BeeNames.class.getResourceAsStream("/pbzh/bees.json")) {
            if (in == null) {
                return;                      // 表没打进来就什么都不做，绝不抛异常影响游戏
            }
            // 用 Gson 实例，不用 JsonParser 的静态方法：`JsonParser.parseReader` 是
            // Gson 2.8.6 才加的，1.17.1 那批 Minecraft 自带的 Gson 比它老，编不过；
            // `Gson#fromJson(Reader, Class)` 从 Gson 1.x 一路都在。
            JsonObject root = new Gson().fromJson(
                    new InputStreamReader(in, StandardCharsets.UTF_8), JsonObject.class);
            if (root == null) {
                return;
            }
            fill(root, "id2zh", ID2ZH);
            fill(root, "en2zh", EN2ZH);
            fill(root, "type2zh", TYPE2ZH);
        } catch (Exception ignored) {
            // 显示层出错绝不能影响游戏：宁可不翻
        }
    }

    private static void fill(JsonObject root, String key, Map<String, String> into) {
        if (!root.has(key)) {
            return;
        }
        for (Map.Entry<String, com.google.gson.JsonElement> e
                : root.getAsJsonObject(key).entrySet()) {
            into.put(e.getKey(), e.getValue().getAsString());
        }
    }

    public static String translate(String s) {
        String out = s;

        // 形态1：原始 ID
        Matcher m = RAW_ID.matcher(out);
        // 用 StringBuffer 不用 StringBuilder：`Matcher#appendReplacement(StringBuilder,…)`
        // 是 Java 9 才加的重载，1.16 及更早那批目标跑 Java 8，编不过。
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            String base = m.group(1);
            String stripped = base.endsWith("_bee")
                    ? base.substring(0, base.length() - 4) : base;
            String zh = ID2ZH.get(stripped);
            if (zh == null) {
                zh = ID2ZH.get(base);
            }
            m.appendReplacement(sb, Matcher.quoteReplacement(zh != null ? zh : m.group()));
        }
        m.appendTail(sb);
        out = sb.toString();

        // 形态2：英文整名（歧义名已在生成期剔除）
        if (EN_NAMES != null) {
            m = EN_NAMES.matcher(out);
            sb = new StringBuffer();
            while (m.find()) {
                String zh = EN2ZH.get(m.group());
                m.appendReplacement(sb, Matcher.quoteReplacement(zh != null ? zh : m.group()));
            }
            m.appendTail(sb);
            out = sb.toString();
        }

        // 形态3：类型行 —— 整段精确匹配，不做贪婪替换
        m = TYPE_LINE.matcher(out);
        sb = new StringBuffer();
        while (m.find()) {
            String zh = TYPE2ZH.get(m.group(3));
            m.appendReplacement(sb, Matcher.quoteReplacement(
                    m.group(1) + m.group(2) + (zh != null ? zh : m.group(3)) + m.group(4)));
        }
        m.appendTail(sb);
        out = sb.toString();

        // 形态4：原版蜜蜂的括号整名
        return out.replace("(Bee)", "(蜜蜂)");
    }
}
