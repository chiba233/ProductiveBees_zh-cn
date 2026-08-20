// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.player.ItemTooltipEvent;
import net.minecraftforge.fml.loading.FMLEnvironment;
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
        BeeNames.hello("Forge");
        // **显示层的监听器只在客户端注册。** 这几个事件类引用了客户端专有类型
        // （1.15.2 的 ItemTooltipEvent 就带着 net.minecraft.client.util.ITooltipFlag），
        // 而 EventBus 注册时要反射事件类的构造器——在专用服务器上就是
        // NoClassDefFoundError，整个 mod 加载失败、服务器起不来。
        // 这不是新引入的问题：把老版本装进服务端一直都会崩，只是以前没人这么装。
        if (FMLEnvironment.dist.isClient()) {
            MinecraftForge.EVENT_BUS.addListener(ForgeEntry::onItemTooltip);
            try {
                MinecraftForge.EVENT_BUS.addListener(ForgeEntry::onRenderNameTag);
            } catch (Throwable ignored) {
                // 挂不上顶多是名牌还显示英文
            }
            // 每 tick 一次；方法自己先比语言表的对象身份，没换过立刻返回
            try {
                MinecraftForge.EVENT_BUS.addListener(
                        (net.minecraftforge.event.TickEvent.ClientTickEvent e) -> tick());
            } catch (Throwable ignored) {
                // 注册不上顶多是整合包自定义的蜂名不翻，不能因此让 mod 装不上
            }
        }
        ServerCompat.ignoreOnServers();
    }

    /** 每 tick 一次；两个方法自己都先比对象身份，没换过立刻返回。 */
    private static void tick() {
        AddonNames.refresh();
        BeeData.refresh();
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

    /**
     * 世界里那只蜂头顶的名牌——**显示层**，不碰任何数据。
     *
     * <p>只翻**系统生成名**：当前那串字必须在「模组自己生成的英文名」表里才动手，
     * 玩家用命名牌起的名字原样显示，和物品栏、Jade 那边保持一致。
     */
    static void onRenderNameTag(net.minecraftforge.client.event.RenderNameTagEvent event) {
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
