// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.Map;

/**
 * 把数据包定义的蜂名改成中文——**在数据加载完之后动手，不跟数据包抢顺序**。
 *
 * <p>1.15.2 – 1.16.4 的蜂名不走翻译键：`BeeCreator.create` 把蜂数据 JSON 里的
 * `name` 原样写进 NBT，没写就按 id 拼一个英文的；显示时走
 * `entity.productivebees.bee_configurable`（原文是裸的 `%s`）把那串原样塞进去。
 *
 * <p>原先的办法是随包发一份同路径的蜂数据、把 `name` 填成中文，指望它盖住模组
 * 自带那份。**这条路靠不住**：谁盖谁取决于数据包的先后，而那个顺序我们控制不了。
 * 测试者 1.15.2 的日志里是这样的：
 *
 * <pre>
 *   Reloading ResourceManager: productivebees-zh_cn-….jar, jei-….jar,
 *                              Default, forge-….jar, productivebees-1.15.2-….jar
 * </pre>
 *
 * 后面的盖前面的——我们排第一，模组本体排最后，于是我们那份被整个盖掉，蜂名还是
 * 英文。同一个包在 1.16.4 上顺序恰好相反就生效了，这种「看运气」的东西不能留。
 *
 * <p>所以改成等它加载完再动：`BeeReloadListener.INSTANCE.getData()` 是模组自己
 * 公开的方法，返回那张「蜂 id → NBT」的表。数据包谁赢都无所谓，最后落到这张表里
 * 的就是它，我们把 `name` 改掉，三条渲染路径（物品栏、手持、JEI）读到的就都是中文。
 *
 * <p>**只改还是英文的那些**：已经是中文的（我们的数据包赢了、或者模组自带中文）
 * 一律不碰。找不到类、找不到方法、表是空的，全都直接返回——补不上顶多显示英文。
 */
final class BeeData {

    private static Object seen;
    private static Method put;

    private BeeData() {
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

    /**
     * 按形状找 NBT 上的方法：名字各版本是 SRG 的 {@code func_74778_a}，靠不住；
     * 但「两个 String 参数、无返回」的只有 putString 一个。名字对得上就直接用。
     */
    private static Method find(Class<?> c, Class<?> ret, Class<?>... params) {
        Method shaped = null;
        for (Method m : c.getMethods()) {
            if (m.getParameterCount() != params.length || m.getReturnType() != ret) {
                continue;
            }
            boolean hit = true;
            for (int i = 0; i < params.length; i++) {
                if (m.getParameterTypes()[i] != params[i]) {
                    hit = false;
                    break;
                }
            }
            if (!hit) {
                continue;
            }
            if (m.getName().equals("putString") || m.getName().equals("getString")) {
                return m;
            }
            if (shaped != null) {
                return null;               // 形状撞了两个，不猜
            }
            shaped = m;
        }
        return shaped;
    }

    /**
     * 每 tick 调一次；表没换过就立刻返回。资源/数据重载后这张表是新的，那一次才动手。
     */
    static void refresh() {
        try {
            Class<?> c;
            try {
                c = Class.forName("cy.jdkdigital.productivebees.setup.BeeReloadListener");
            } catch (Throwable notInstalled) {
                return;                    // 没装资源蜜蜂，没什么可改的
            }
            Object inst = null;
            for (Field f : c.getDeclaredFields()) {
                if (Modifier.isStatic(f.getModifiers()) && c.isAssignableFrom(f.getType())) {
                    f.setAccessible(true);
                    inst = f.get(null);
                    break;
                }
            }
            if (inst == null) {
                return;
            }
            Method getData = null;
            for (Method m : c.getMethods()) {
                if (m.getParameterCount() == 0 && Map.class.isAssignableFrom(m.getReturnType())) {
                    getData = m;
                    break;
                }
            }
            if (getData == null) {
                return;
            }
            Object raw = getData.invoke(inst);
            if (!(raw instanceof Map) || ((Map<?, ?>) raw).isEmpty() || raw == seen) {
                return;
            }
            seen = raw;
            @SuppressWarnings("unchecked")
            Map<String, Object> data = (Map<String, Object>) raw;
            Map<String, String> id2zh = BeeNames.idTable();
            Method get = null;
            int n = 0;
            for (Map.Entry<String, Object> e : data.entrySet()) {
                Object nbt = e.getValue();
                if (nbt == null) {
                    continue;
                }
                if (put == null || !put.getDeclaringClass().isInstance(nbt)) {
                    put = find(nbt.getClass(), void.class, String.class, String.class);
                    get = find(nbt.getClass(), String.class, String.class);
                }
                if (put == null || get == null) {
                    return;
                }
                Object cur = get.invoke(nbt, "name");
                if (cur instanceof String && cjk((String) cur)) {
                    continue;              // 已经是中文，不碰
                }
                String zh = lookup(id2zh, e.getKey());
                if (zh == null) {
                    continue;
                }
                put.invoke(nbt, "name", zh);
                n++;
            }
            if (n > 0) {
                System.out.println("[productivebees_zh_cn] 数据包定义的蜂名改回中文 "
                        + n + " 只");
            }
        } catch (Throwable ignored) {
            // 显示层永远不许把游戏搞崩：宁可不翻
        }
    }

    /** 键可能是 `lapis`、`gems/emerald`、也可能带命名空间；都试一遍。 */
    private static String lookup(Map<String, String> id2zh, String key) {
        if (key == null) {
            return null;
        }
        String zh = id2zh.get(key);
        if (zh != null) {
            return zh;
        }
        int slash = key.lastIndexOf('/');
        int colon = key.lastIndexOf(':');
        int cut = Math.max(slash, colon);
        return cut >= 0 ? id2zh.get(key.substring(cut + 1)) : null;
    }
}
