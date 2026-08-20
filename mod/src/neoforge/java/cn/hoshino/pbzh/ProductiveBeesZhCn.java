// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化（独立发布）
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;

/**
 * 显示层。除了改字，什么都不做——不注册方块物品、不动配方、不发网络包。
 *
 * <p><b>不再限定 {@code dist = Dist.CLIENT}</b>：蜂笼里那个名字是**捕捉的一瞬间
 * 由服务端**解析成死字符串写进物品的（见 {@link CageNames}），服务端没有中文就
 * 永远是英文，客户端够不着。所以这个 mod 在服务端也要跑，只做一件事：把那批
 * 蜂笼里那个已经固化的英文名改回中文，玩家自己起的名字一个不碰。
 *
 * <p>服务端不装也照样能进服：`displayTest` 声明了忽略版本差异，而且这里对存档的
 * 改动只有「纯显示字段」这一处。
 */
@Mod(ProductiveBeesZhCn.MODID)
public final class ProductiveBeesZhCn {
    public static final String MODID = "productivebees_zh_cn";

    public ProductiveBeesZhCn(IEventBus modBus) {
        // ItemTooltipEvent 在游戏总线上，不在 mod 总线上；它是双端事件，
        // 服务端注册了也只是没人触发，不会出错
        NeoForge.EVENT_BUS.addListener(TooltipHook::onItemTooltip);
        // 服务端那一条：蜂笼里固化的名字。只有蜂笼的 NBT 需要服务端插手
        NeoForge.EVENT_BUS.addListener(ServerNames::onPlayerTick);
        // 每 tick 一次；方法自己先比语言表对象身份，没换过立刻返回。
        // 资源重载后语言表是新对象，那一次才真正去学整合包自己加的蜂名。
        try {
            NeoForge.EVENT_BUS.addListener(
                    net.neoforged.neoforge.client.event.ClientTickEvent.Post.class,
                    e -> tick());
        } catch (Throwable ignored) {
            // 注册不上顶多是整合包自定义的蜂名不翻，不能因此让 mod 装不上
        }
    }

    /** 每 tick 一次；两个方法自己都先比对象身份，没换过立刻返回。 */
    private static void tick() {
        AddonNames.refresh();
        BeeData.refresh();
    }
}
