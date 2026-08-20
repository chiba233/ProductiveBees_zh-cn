// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.neoforged.neoforge.event.entity.EntityJoinLevelEvent;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;

import java.util.List;

/**
 * 服务端这一侧：把**已经固化进物品和实体里**的英文蜂名改回中文。
 *
 * <p>为什么客户端做不到，见 {@link CageNames} 的注释——那个名字在捕捉的一瞬间
 * 就被解析成死字符串写进了物品数据，由**服务端**的语言表决定。
 *
 * <p>两个入口，和判断逻辑分开：这里只负责把 NBT 掏出来、把结果写回去，
 * 「要不要改、改成什么」全在 {@link CageNames}（那个类不碰 Minecraft，能单测）。
 *
 * <ul>
 *   <li>玩家背包每 100 tick 扫一次：只看蜂笼，只改 `custom_data` 里的 `name`；</li>
 *   <li>实体进入世界时：只看**带自定义名**的资源蜜蜂实体（从蜂笼放出来的那些）。</li>
 * </ul>
 *
 * <p>整段包在 try/catch 里：这是显示层的锦上添花，**绝不允许它把服务器搞崩**。
 */
final class ServerNames {

    private ServerNames() {
    }

    static void onPlayerTick(PlayerTickEvent.Post event) {
        Player p = event.getEntity();
        // 服务端才算数：客户端那份物品是同步来的副本，改了下一次同步就没了
        if (p.level().isClientSide() || p.tickCount % 100 != 0) {
            return;
        }
        try {
            Inventory inv = p.getInventory();
            fix(inv.items);
            fix(inv.offhand);
        } catch (Throwable ignored) {
            // 名字没改成顶多显示英文，不能因此影响玩家
        }
    }

    private static void fix(List<ItemStack> list) {
        for (int i = 0; i < list.size(); i++) {
            ItemStack stack = list.get(i);
            if (stack.isEmpty()
                    || !stack.getItem().getDescriptionId().contains("bee_cage")) {
                continue;
            }
            CustomData cd = stack.get(DataComponents.CUSTOM_DATA);
            if (cd == null) {
                continue;
            }
            CompoundTag tag = cd.copyTag();
            if (!tag.contains("name")) {
                continue;
            }
            String zh = CageNames.rename(tag.getString("type"),
                    tag.getString("entity"), tag.getString("name"));
            if (zh == null) {
                continue;
            }
            tag.putString("name", zh);
            stack.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
        }
    }

    static void onEntityJoin(EntityJoinLevelEvent event) {
        Entity e = event.getEntity();
        if (event.getLevel().isClientSide() || !e.hasCustomName()) {
            return;
        }
        try {
            String type = e.getType().builtInRegistryHolder().key().location().toString();
            if (!type.startsWith("productivebees:")) {
                return;
            }
            Component name = e.getCustomName();
            if (name == null) {
                return;
            }
            // 数据包定义的蜂都是同一个实体类型，真实身份在它自己的 NBT 里
            String inner = null;
            CompoundTag nbt = new CompoundTag();
            e.saveWithoutId(nbt);
            if (nbt.contains("type")) {
                inner = nbt.getString("type");
            }
            String zh = CageNames.rename(inner, type, name.getString());
            if (zh != null) {
                e.setCustomName(Component.literal(zh));
            }
        } catch (Throwable ignored) {
            // 同上：改不动就算了
        }
    }
}
