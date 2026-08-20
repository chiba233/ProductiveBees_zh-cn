// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import java.util.Map;

/**
 * 决定一个**已经固化在物品/实体上的蜂名**要不要改、改成什么。
 *
 * <p>蜂笼的名字不是翻译键。`BeeCage` 在**捕捉的那一刻**就把显示名解析成一个普通
 * 字符串写进了物品数据：
 *
 * <pre>
 *   nbt.putString("name", bee.getName().getString());   // 服务端执行
 *   // 显示时： Component.translatable("item…bee_cage").append(" (" + name + ")")
 * </pre>
 *
 * 谁抓的就按谁的语言表解析。服务端只有英文，写进去的就是 `Dark Steel Bee`，
 * 之后客户端再怎么翻都够不着它——那已经不是键，是一段死字符串。所以这件事
 * **只能在服务端、在数据这一侧**做。
 *
 * <p>这个类里没有一个 Minecraft 类型，胶水在各加载器那一份里，方便脱离游戏测。
 *
 * <p><b>安全闸</b>：改错玩家的物品比显示英文严重得多，所以三道都过了才动手：
 * <ol>
 *   <li>当前名字里有汉字 → 不碰（已经是中文，或者玩家自己起的中文名）；</li>
 *   <li>当前名字**不在**「模组自己生成的英文名」表里 → 不碰
 *       （玩家用命名牌起的英文名长这样，绝不能动）；</li>
 *   <li>按蜂的 **id** 查权威译名——不是拿英文名反查。英文名只用来判断
 *       「这是不是系统生成的」，改成什么由 id 说了算。</li>
 * </ol>
 */
public final class CageNames {

    private CageNames() {
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

    /** `productivebees:dark_steel`、`dark_steel_bee`、`dark_steel` 都试一遍。 */
    private static String byId(String id) {
        if (id == null || id.isEmpty()) {
            return null;
        }
        Map<String, String> t = BeeNames.idTable();
        String s = id;
        int cut = Math.max(s.lastIndexOf(':'), s.lastIndexOf('/'));
        if (cut >= 0) {
            s = s.substring(cut + 1);
        }
        String zh = t.get(s);
        if (zh == null && s.endsWith("_bee")) {
            zh = t.get(s.substring(0, s.length() - 4));
        }
        return zh;
    }

    /**
     * @param typeId   蜂笼 NBT 里的 `type`（数据包定义的蜂用这个），可为 null
     * @param entityId 蜂笼 NBT 里的 `entity`（注册实体用这个），可为 null
     * @param current  当前固化在物品上的那个名字
     * @return 要写回去的中文名；不该动就返回 null
     */
    public static String rename(String typeId, String entityId, String current) {
        if (current == null || current.isEmpty() || cjk(current)) {
            return null;
        }
        if (!BeeNames.enTable().containsKey(current)) {
            return null;                       // 不是模组生成的名字：玩家自己起的
        }
        String zh = byId(typeId);
        if (zh == null) {
            zh = byId(entityId);
        }
        return zh == null || zh.equals(current) ? null : zh;
    }
}
