// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化（独立发布）
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.event.entity.player.ItemTooltipEvent;

import java.util.List;

/**
 * 事件胶水：把 {@link BeeNames#translate} 挂到 tooltip 上。
 *
 * <p>只有这一个类碰 Minecraft 的类型，真逻辑都在 {@link BeeNames} 里，
 * 那边能脱离游戏直接跑测试。
 */
final class TooltipHook {
    private TooltipHook() {
    }

    static void onItemTooltip(ItemTooltipEvent event) {
        try {
            ItemStack stack = event.getItemStack();
            if (!stack.getDescriptionId().contains("productivebees")) {
                return;                      // 只碰这个模组的物品
            }
            List<Component> lines = event.getToolTip();
            for (int i = 0; i < lines.size(); i++) {
                Component line = lines.get(i);
                String s = line.getString();
                String ns = BeeNames.translate(s);
                if (!ns.equals(s)) {
                    lines.set(i, Component.literal(ns).setStyle(line.getStyle()));
                }
            }
        } catch (Exception ignored) {
            // 显示层永远不许把游戏搞崩：宁可不翻
        }
    }
}
