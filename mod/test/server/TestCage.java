// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// 服务端那条路的**真机验证**：对着打好的 jar、在真的 Minecraft 服务端类路径上，
// 造一个真的 ItemStack 走真的组件读写。不需要世界、不需要玩家、不用进服——
// 起个原版 Bootstrap 就够。
//
// 为什么必须这么测：蜂笼改名平时只在「玩家背包每 100 tick 扫一次」里走到，
// 没有客户端连进来就永远不触发，等于这段管道没有任何机械兜底。
package cn.hoshino.pbzh;

import net.minecraft.SharedConstants;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.CustomData;

public class TestCage {
    static int failed = 0;

    static ItemStack cage(String type, String name) {
        ItemStack s = new ItemStack(Items.STONE);       // 哪个物品不重要，测的是组件读写
        CompoundTag t = new CompoundTag();
        t.putString("type", type);
        t.putString("name", name);
        s.set(DataComponents.CUSTOM_DATA, CustomData.of(t));
        return s;
    }

    static String nameOf(ItemStack s) {
        CustomData cd = s.get(DataComponents.CUSTOM_DATA);
        return cd == null ? null : cd.copyTag().getString("name");
    }

    static void check(String label, String type, String before, String want) {
        ItemStack s = cage(type, before);
        ServerNames.rename(s);
        String got = nameOf(s);
        boolean ok = want.equals(got);
        if (!ok) {
            failed++;
        }
        System.out.println((ok ? "  ok  " : "  ❌  ") + label + "  " + before + " → " + got);
        if (!ok) {
            System.out.println("      期望 " + want);
        }
    }

    public static void main(String[] args) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        String type = args.length > 0 ? args[0] : "productivebees:abominable";
        String en = args.length > 1 ? args[1] : "Abominable Bee";
        String zh = args.length > 2 ? args[2] : "憎恶蜜蜂";
        check("系统生成名改成中文", type, en, zh);
        check("已经是中文不重复改", type, zh, zh);
        check("玩家命名牌起的名字不碰", type, "My Best Bee 001", "My Best Bee 001");
        check("中文自定义名不碰", type, "我的小蜜蜂", "我的小蜜蜂");
        check("id 不认识就不改", "productivebees:zzz_not_a_bee", en, en);
        System.out.println(failed == 0 ? "✅ 蜂笼组件读写全部通过" : "❌ " + failed + " 项没过");
        if (failed > 0) {
            System.exit(1);
        }
    }
}
