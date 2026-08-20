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
        // 每 tick 一次，但方法自己先比语言表的对象身份，没换过立刻返回。
        // 资源重载后语言表是新对象，那一次才真正去学整合包自己加的蜂名。
        try {
            MinecraftForge.EVENT_BUS.addListener(
                    (net.minecraftforge.event.TickEvent.ClientTickEvent e) ->
                            tick());
        } catch (Throwable ignored) {
            // 注册不上顶多是整合包自定义的蜂名不翻，不能因此让 mod 装不上
        }
        // 名牌是客户端事件，类在服务端不存在，所以用 try 兜住
        try {
            MinecraftForge.EVENT_BUS.addListener(ForgeEntry::onRenderNameTag);
        } catch (Throwable ignored) {
            // 挂不上顶多是名牌还显示英文
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
                    lines.set(i, new TextComponent(ns).setStyle(line.getStyle()));
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
    static void onRenderNameTag(net.minecraftforge.client.event.RenderNameplateEvent event) {
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
                event.setContent(new TextComponent(ns));
            }
        } catch (Throwable ignored) {
            // 显示层永远不许把游戏搞崩：宁可名牌还是英文
        }
    }
}
