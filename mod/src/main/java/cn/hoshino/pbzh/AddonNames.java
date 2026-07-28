// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 翻整合包**自己加的**那些蜂——名字从玩家自己装的模组里现学。
 *
 * <p>整合包用数据包给资源蜜蜂加蜂，键长这样：
 *
 * <pre>
 *   entity.productivebees.tiberium_bee        Tiberium Bee
 *   item.productivebees.honeycomb_tiberium    Tiberium Comb
 *   block.productivebees.comb_tiberium        Tiberium Comb Block
 * </pre>
 *
 * <p>这些键不在模组本体里，我们的语言文件自然也没有。以前的做法是把整合包一个个
 * 扫过来、把材料名一条条手写进词表——但那只覆盖扫过的包。拿留一包检验量过：
 * 换一个没扫过的整合包，只有约三成能对上，七成照样是英文。
 *
 * <p>症结在于「tiberium 的中文是什么」这件事**我们本来就不该知道**——那是别的
 * 模组的专有名词。但玩家的游戏里知道：他要么装了那个模组的官方中文，要么装了
 * 社区汉化包。所以这里改成运行期现查：
 *
 * <pre>
 *   1. 找这个材料的**基础形态**条目            item.xxx.tiberium_ingot = 泰伯利亚锭
 *   2. 去掉量词，每条投一票                    锭 → 泰伯利亚；块 → 泰伯利亚
 *   3. 七成以上的票投给同一个词才认            泰伯利亚
 *   4. 按形状拼                                泰伯利亚 + 蜜蜂
 * </pre>
 *
 * <p>这样做还顺带对了一件事：**跟着玩家自己的叫法走**。他那份汉化把 tiberium 叫
 * 什么，蜂就叫什么，不会出现「蜂叫泰伯利亚、矿叫泰矿」这种两张皮。反过来，玩家
 * 要是压根没装那个模组的中文，这里也查不到，就保持英文——那正好和他游戏里其余
 * 部分一致。
 *
 * <p>拼不出的一条都不硬填：宁可显示英文，也不出「Tiberium蜜蜂」这种半截货。
 *
 * <p>这个类里**没有一个 Minecraft 类型**（{@link #compose} 收一张普通 Map），
 * 所以能脱离游戏直接测；碰游戏的只有 {@link #refresh()} 那一小段反射。
 */
public final class AddonNames {

    /** 键的形状 → 中文怎么拼。与 scripts/addon_lang.py 的 SHAPES 一一对应。 */
    private static final String[][] SHAPES = {
        {"entity.productivebees.", "_bee", "%s蜜蜂"},
        {"item.productivebees.spawn_egg_", "_bee", "%s蜜蜂刷怪蛋"},
        {"item.productivebees.honeycomb_", "", "%s蜜脾"},
        {"item.productivebees.configurable_honeycomb_", "", "%s蜜脾"},
        {"block.productivebees.comb_", "", "%s蜜脾块"},
    };

    /**
     * 只认这几种**基础材料形态**当样本，附带它们中文的量词。
     *
     * <p>不能拿所有以材料开头的条目当样本：`fiery_blood`（炽热的血液）、
     * `fiery_tears`（血泪成河）、`ironwood_planks`（铁色木木板）都以材料开头，
     * 但它们的中文跟材料名对不上，混进来算公共前缀就会把「炽铁」削成「炽」。
     *
     * <p>基础形态则是定义性的：`<材料>_ingot` 的中文必然是「<材料>锭」，
     * 去掉「锭」就是材料本身。
     */
    private static final String[][] FORMS = {
        {"ingot", "锭"}, {"block", "块"}, {"nugget", "粒"}, {"dust", "粉", "尘"},
        {"gem", "宝石"}, {"ore", "矿石", "矿"}, {"plate", "板"}, {"rod", "棒"},
        {"sheet", "板", "片"}, {"gear", "齿轮"}, {"raw", ""},
    };

    /** 学一个材料至少要几票。一票没法判断那截是材料还是成品。 */
    private static final int MIN_SAMPLES = 2;
    /** 材料 id 太短容易在别的键里瞎命中（ore、gem 之类）。 */
    private static final int MIN_ID = 4;
    /** 学出来的材料名超过这个长度多半是整句，不是材料。 */
    private static final int MAX_TERM = 10;
    private static final double MAJORITY = 0.7;

    private static Object seen;

    private AddonNames() {
    }

    private static boolean cjk(String s) {
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c >= 0x4E00 && c <= 0x9FFF) {
                return true;
            }
        }
        return false;
    }

    private static boolean latin(String s) {
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {
                return true;
            }
        }
        return false;
    }

    /**
     * 收一张「翻译键 → 当前显示文本」的表，返回该补哪些键。
     *
     * <p>**只扫两遍全表**，不是每个蜂键扫一遍。语言表在大整合包里有十几万条，
     * 而资源蜜蜂的键上千；逐个去重扫是十几万乘上千次字符串比较，一次就能把
     * 客户端卡住好几秒——玩家眼里那和崩溃没区别。这个方法每 tick 会被叫到。
     *
     * <p>第一遍先记下「哪些材料需要中文」，第二遍才去收它们的票。
     */
    public static Map<String, String> compose(Map<String, String> lang) {
        // 第一遍：哪些蜂键还是英文，它们要哪些材料
        Map<String, String> todo = new LinkedHashMap<>();
        Map<String, String> wantShape = new HashMap<>();
        for (Map.Entry<String, String> e : lang.entrySet()) {
            String key = e.getKey();
            String cur = e.getValue();
            if (cur == null || cjk(cur) || !latin(cur)) {
                continue;                       // 已经是中文，或没有字母，不碰
            }
            for (String[] shape : SHAPES) {
                if (!key.startsWith(shape[0]) || !key.endsWith(shape[1])) {
                    continue;
                }
                String id = key.substring(shape[0].length(),
                                          key.length() - shape[1].length());
                if (id.length() >= MIN_ID && id.indexOf('.') < 0) {
                    todo.put(key, id);
                    wantShape.put(key, shape[2]);
                }
                break;
            }
        }
        if (todo.isEmpty()) {
            return new LinkedHashMap<>();
        }
        Map<String, Map<String, Integer>> votes = collect(lang, todo.values());

        Map<String, String> out = new LinkedHashMap<>();
        Map<String, String> terms = new HashMap<>();
        for (Map.Entry<String, String> e : todo.entrySet()) {
            String id = e.getValue();
            if (!terms.containsKey(id)) {
                terms.put(id, decide(votes.get(id)));
            }
            String zh = terms.get(id);
            if (zh != null) {
                out.put(e.getKey(), String.format(wantShape.get(e.getKey()), zh));
            }
        }
        return out;
    }

    /**
     * 第二遍：单遍扫全表，把需要的那些材料的票收齐。
     *
     * <p>只认**基础形态**的条目投票：`<材料>_ingot` 的中文必然是「<材料>锭」，
     * 去掉「锭」就是材料本身。工具、盔甲、告示牌不算——`fiery_sword`（炽焰剑）、
     * `fiery_blood`（炽热的血液）都以材料开头，中文却跟材料名对不上。
     */
    private static Map<String, Map<String, Integer>> collect(
            Map<String, String> lang, Iterable<String> wanted) {
        java.util.Set<String> want = new java.util.HashSet<>();
        for (String id : wanted) {
            want.add(id);
        }
        Map<String, Map<String, Integer>> votes = new HashMap<>();
        for (Map.Entry<String, String> e : lang.entrySet()) {
            String k = e.getKey();
            String v = e.getValue();
            if (v == null || v.length() > MAX_TERM + 4 || !cjk(v) || latin(v)) {
                continue;
            }
            if (k.startsWith("productivebees.") || k.contains(".productivebees.")) {
                continue;                       // 不拿资源蜜蜂自己的条目当样本，避免自举
            }
            int dot = k.lastIndexOf('.');
            String tail = dot < 0 ? k : k.substring(dot + 1);
            for (String[] form : FORMS) {
                String suffix = form[0];
                String id;
                if (suffix.isEmpty()) {
                    id = tail;
                } else if (tail.length() > suffix.length() + 1
                        && tail.endsWith(suffix)
                        && tail.charAt(tail.length() - suffix.length() - 1) == '_') {
                    id = tail.substring(0, tail.length() - suffix.length() - 1);
                } else {
                    continue;
                }
                if (!want.contains(id)) {
                    continue;
                }
                String word = drop(v, form);
                if (word != null) {
                    Map<String, Integer> box = votes.get(id);
                    if (box == null) {
                        box = new LinkedHashMap<>();
                        votes.put(id, box);
                    }
                    Integer had = box.get(word);
                    box.put(word, had == null ? 1 : had + 1);
                }
                break;
            }
        }
        return votes;
    }

    /** 去掉中文里的量词（锭 / 块 / 粉…）；量词对不上就不猜，返回 null。 */
    private static String drop(String value, String[] form) {
        for (int i = 1; i < form.length; i++) {
            String cn = form[i];
            if (cn.isEmpty()) {
                return value;
            }
            if (value.endsWith(cn) && value.length() > cn.length()) {
                return value.substring(0, value.length() - cn.length());
            }
        }
        return null;
    }

    /**
     * 票数够、且七成以上投给同一个词，才认这个材料的中文。
     *
     * <p>两个模组对同一个 id 有两种译法（`ironwood` 在暮色森林叫铁木、在别处叫
     * 铁色木）时票会分裂，这里就返回 null——那一条保持英文。
     *
     * <p>这条取舍是照着事故等级定的：**把游戏搞崩是 P0，把名字翻错也是 P0；
     * 少翻一条只是个 issue。** 所以拿不准一律不翻。
     */
    private static String decide(Map<String, Integer> box) {
        if (box == null) {
            return null;
        }
        int total = 0;
        int most = 0;
        String best = null;
        for (Map.Entry<String, Integer> e : box.entrySet()) {
            total += e.getValue();
            if (e.getValue() > most) {
                most = e.getValue();
                best = e.getKey();
            }
        }
        if (best == null || total < MIN_SAMPLES || most < MIN_SAMPLES
                || most < total * MAJORITY || best.length() > MAX_TERM || !cjk(best)) {
            return null;
        }
        return best;
    }

    /**
     * 把学到的补进当前语言表。**每次资源重载后跑一次**，跑之前先比对象身份，
     * 没换过就立刻返回——这个方法会被每 tick 调到。
     *
     * <p>任何一步够不着就整段放弃：补不上顶多是那几只蜂显示英文，和现在一样。
     */
    static void refresh() {
        try {
            Object holder = languageHolder();
            if (holder == null || holder == seen) {
                return;
            }
            seen = holder;
            Field f = mapField(holder);
            if (f == null) {
                return;
            }
            @SuppressWarnings("unchecked")
            Map<String, String> lang = (Map<String, String>) f.get(holder);
            if (lang == null || lang.isEmpty()) {
                return;
            }
            Map<String, String> add = compose(lang);
            if (add.isEmpty()) {
                return;
            }
            try {
                lang.putAll(add);
            } catch (UnsupportedOperationException immutable) {
                Map<String, String> copy = new HashMap<>(lang);
                copy.putAll(add);
                f.set(holder, copy);
            }
            // 学到东西才出一行。这个功能的全部意义就是「有没有学到」，
            // 出问题时没有这一行就只能靠猜。学不到就一声不吭。
            System.out.println("[productivebees_zh_cn] 从已装模组现学补上 "
                    + add.size() + " 条整合包蜂名");
        } catch (Throwable ignored) {
            // 显示层永远不许把游戏搞崩：宁可不翻
        }
    }

    /**
     * 当前的语言表对象。
     *
     * <p>**读静态字段，不调方法。** 拿官方混淆表核过：1.16.5 与 1.21.1 的
     * {@code Language} 上都有**两个**静态无参、返回自身类型的方法——
     * {@code getInstance()} 和 {@code loadDefault()}。后者会当场读一份全新的
     * 默认语言表回来，抓错了就是每次重载都做一遍无用的 I/O，还把词条塞进一个
     * 没人用的临时对象。而静态字段 {@code instance} 是唯一的，读它没有副作用。
     *
     * <p>字段名各版本不同（老版本是 SRG 的 {@code field_xxxxx}），所以按**类型**
     * 认：类型就是这个类自己的那个静态字段。真找不到才退回去调名字正好叫
     * {@code getInstance} 的方法，绝不按形状乱挑。
     */
    private static Object languageHolder() throws Exception {
        for (String name : new String[] {"net.minecraft.locale.Language",
                                         "net.minecraft.util.text.LanguageMap"}) {
            Class<?> c;
            try {
                c = Class.forName(name);
            } catch (Throwable notThisVersion) {
                continue;
            }
            for (Field f : c.getDeclaredFields()) {
                if (Modifier.isStatic(f.getModifiers()) && c.isAssignableFrom(f.getType())) {
                    f.setAccessible(true);
                    Object o = f.get(null);
                    if (o != null) {
                        return o;
                    }
                }
            }
            try {
                Method m = c.getMethod("getInstance");
                if (Modifier.isStatic(m.getModifiers())) {
                    Object o = m.invoke(null);
                    if (o != null) {
                        return o;
                    }
                }
            } catch (Throwable noSuchMethod) {
                continue;
            }
        }
        return null;
    }

    /** 原版一定有的几个键：拿它们确认手上这张 Map 真的是语言表，而不是别的缓存。 */
    private static final String[] VANILLA = {"gui.done", "gui.cancel", "menu.options"};

    private static boolean looksLikeLang(Map<?, ?> m) {
        if (m.size() < 100) {
            return false;
        }
        for (String k : VANILLA) {
            if (m.containsKey(k)) {
                return true;
            }
        }
        return false;
    }

    /** 语言表对象里装词条的那个 Map 字段。 */
    private static Field mapField(Object holder) {
        for (Class<?> k = holder.getClass(); k != null && k != Object.class;
                k = k.getSuperclass()) {
            for (Field f : k.getDeclaredFields()) {
                if (Modifier.isStatic(f.getModifiers())
                        || !Map.class.isAssignableFrom(f.getType())) {
                    continue;
                }
                try {
                    f.setAccessible(true);
                    Object v = f.get(holder);
                    // 不只看「是不是 Map」：得真的是语言表才动它
                    if (v instanceof Map && looksLikeLang((Map<?, ?>) v)) {
                        return f;
                    }
                } catch (Throwable ignored) {
                    // 取不到就看下一个字段
                }
            }
        }
        return null;
    }
}
