// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.minecraft.network.chat.Component;
import net.neoforged.neoforge.client.event.RenderNameTagEvent;

/**
 * 世界里那只蜂头顶的名牌——**显示层**，不碰任何数据。
 *
 * <p>为什么实体走显示层、蜂笼走数据层，判据见 {@link CageNames}：蜂笼那个字段有
 * 一堆消费者（tooltip、快捷栏浮动名、JEI、Jade、搜索），只改一个就是半截货，所以
 * 必须改数据；名牌只有渲染这一个消费者，换掉显示就够了，没有理由去动世界里的
 * 实体数据——那是改存档。
 *
 * <p>只翻**系统生成名**：当前这串字必须在「模组自己生成的英文名」表里才动手。
 * 玩家用命名牌起的名字原样显示，和物品栏、Jade 那边保持一致。
 */
final class NameTagHook {

    private NameTagHook() {
    }

    static void onRenderNameTag(RenderNameTagEvent event) {
        try {
            if (!event.getEntity().getType().getDescriptionId()
                    .contains("productivebees")) {
                return;
            }
            Component c = event.getContent();
            if (c == null) {
                return;
            }
            String s = c.getString();
            if (!BeeNames.enTable().containsKey(s)) {
                return;                        // 玩家自己起的名字，不碰
            }
            String ns = BeeNames.translate(s);
            if (!ns.equals(s)) {
                event.setContent(Component.literal(ns));
            }
        } catch (Throwable ignored) {
            // 显示层永远不许把游戏搞崩：宁可名牌还是英文
        }
    }
}
