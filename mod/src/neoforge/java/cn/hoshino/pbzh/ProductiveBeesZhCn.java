// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化（独立发布）
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;

/**
 * 纯客户端显示层。除了改 tooltip 上的字，什么都不做——
 * 不注册方块物品、不动配方、不发网络包、不碰存档数据。
 * 所以它对进服、对存档、对配方零影响。
 */
@Mod(value = ProductiveBeesZhCn.MODID, dist = Dist.CLIENT)
public final class ProductiveBeesZhCn {
    public static final String MODID = "productivebees_zh_cn";

    public ProductiveBeesZhCn(IEventBus modBus) {
        // ItemTooltipEvent 在游戏总线上，不在 mod 总线上
        NeoForge.EVENT_BUS.addListener(TooltipHook::onItemTooltip);
        // 每 tick 一次；方法自己先比语言表对象身份，没换过立刻返回。
        // 资源重载后语言表是新对象，那一次才真正去学整合包自己加的蜂名。
        NeoForge.EVENT_BUS.addListener(
                net.neoforged.neoforge.event.tick.ClientTickEvent.Post.class,
                e -> AddonNames.refresh());
    }
}
