// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.player.ItemTooltipEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.List;

/**
 * Forge（1.17 – 1.20.1，以及 1.20.1 的 NeoForge）用的入口。
 *
 * <p>与 NeoForge 那一份的区别只有包名：事件类在 {@code net.minecraftforge.*} 下。
 * 真逻辑都在 {@link BeeNames}，那个类不引用任何 Minecraft 类型，两边共用。
 *
 * <p>没有走 {@code @Mod(dist = ...)}：那是 NeoForge 才有的写法。「服务端没有也
 * 没关系」这一声明也不能指望 {@code mods.toml} 的 {@code displayTest}——这几版的
 * 加载器根本不读那个键，得在代码里注册扩展点，见 {@link ServerCompat}。
 */
@Mod(ForgeEntry.MODID)
public final class ForgeEntry {
    public static final String MODID = "productivebees_zh_cn";

    public ForgeEntry() {
        MinecraftForge.EVENT_BUS.addListener(ForgeEntry::onItemTooltip);
        // 每 tick 一次，但方法自己先比语言表的对象身份，没换过立刻返回。
        // 资源重载后语言表是新对象，那一次才真正去学整合包自己加的蜂名。
        try {
            MinecraftForge.EVENT_BUS.addListener(
                    (net.minecraftforge.event.TickEvent.ClientTickEvent e) ->
                            AddonNames.refresh());
        } catch (Throwable ignored) {
            // 注册不上顶多是整合包自定义的蜂名不翻，不能因此让 mod 装不上
        }
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
                    lines.set(i, Component.literal(ns).setStyle(line.getStyle()));
                }
            }
        } catch (Exception ignored) {
            // 显示层永远不许把游戏搞崩：宁可不翻
        }
    }
}
