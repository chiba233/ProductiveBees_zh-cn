// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
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
 * <p><b>只处理蜂笼</b>：需要服务端插手的只有蜂笼那份 NBT。从蜂笼放出来的蜜蜂，
 * 它的 `CustomName` 就是蜂笼里存的那个名字——蜂笼修好了，放出来自然是中文，
 * 不必再去动世界里的实体（那是改存档，风险大而且没必要）。
 *
 * <p>玩家背包每 100 tick 扫一次，只看蜂笼，只改 `custom_data` 里的 `name`。
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
            rename(stack);
        }
    }

    /**
     * 把一个蜂笼上固化的名字改成中文；改了返回 true。
     *
     * <p>单独拆出来是**为了能测**：这段是纯组件读写（`CUSTOM_DATA` 取出来、
     * 改一个字段、写回去），不需要世界也不需要玩家，起个原版 Bootstrap 就能验。
     * 埋在背包循环里的话，只有真有玩家在线才走得到，等于没有机械兜底。
     */
    static boolean rename(ItemStack stack) {
        CustomData cd = stack.get(DataComponents.CUSTOM_DATA);
        if (cd == null) {
            return false;
        }
        CompoundTag tag = cd.copyTag();
        if (!tag.contains("name")) {
            return false;
        }
        String zh = CageNames.rename(tag.getString("type"),
                tag.getString("entity"), tag.getString("name"));
        if (zh == null) {
            return false;
        }
        tag.putString("name", zh);
        stack.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
        return true;
    }
}
