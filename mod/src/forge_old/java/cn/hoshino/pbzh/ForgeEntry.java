// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.TextComponent;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.player.ItemTooltipEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.List;

/**
 * Forge 1.18 及更早用的入口。
 *
 * <p>与 NeoForge 那一份的区别只有包名：事件类在 {@code net.minecraftforge.*} 下。
 * 真逻辑都在 {@link BeeNames}，那个类不引用任何 Minecraft 类型，两边共用。
 *
 * <p>与 {@code src/forge} 那份只差一处：{@code Component.literal()} 是 1.19 才有的，
 * 1.18 及更早要用 {@code new TextComponent()}。为这一个方法单开一套源目录，
 * 比在代码里反射兜圈子清楚。
 *
 * <p>「服务端没有也没关系」这一声明不能指望 {@code mods.toml} 的
 * {@code displayTest}——这几版的加载器根本不读那个键，见 {@link ServerCompat}。
 */
@Mod(ForgeEntry.MODID)
public final class ForgeEntry {
    public static final String MODID = "productivebees_zh_cn";

    public ForgeEntry() {
        MinecraftForge.EVENT_BUS.addListener(ForgeEntry::onItemTooltip);
        ServerCompat.ignoreOnServers();
    }

    static void onItemTooltip(ItemTooltipEvent event) {
        try {
            ItemStack stack = event.getItemStack();
            if (!stack.getDescriptionId().contains("productivebees")) {
                return;
            }
            List<Component> lines = event.getToolTip();
            for (int i = 0; i < lines.size(); i++) {
                Component line = lines.get(i);
                String s = line.getString();
                String ns = BeeNames.translate(s);
                if (!ns.equals(s)) {
                    lines.set(i, new TextComponent(ns).setStyle(line.getStyle()));
                }
            }
        } catch (Exception ignored) {
            // 显示层永远不许把游戏搞崩：宁可不翻
        }
    }
}
