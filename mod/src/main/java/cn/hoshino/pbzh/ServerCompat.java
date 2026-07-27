// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import java.lang.reflect.Method;
import java.util.function.BiPredicate;
import java.util.function.Supplier;

/**
 * 告诉加载器：这是纯客户端的显示层，服务端没有它也没关系。
 *
 * <p>不声明的话，进服时加载器会拿客户端的 mod 列表和服务端比，多出来的这一个
 * 就成了「mod 不一致」，玩家被挡在服务器外面。汉化把人挡在服务器外面是这个项目
 * 里最不能接受的一类故障，所以这件事不能只写进 {@code mods.toml} 指望加载器读。
 *
 * <p>因为**中间那一整段版本谁都不读那个字段**：
 *
 * <pre>
 *   1.15 – 1.16          代码注册 ExtensionPoint.DISPLAYTEST（枚举常量）
 *   1.17 – 1.20          代码注册 IExtensionPoint.DisplayTest（类型即扩展点）
 *                        这几版在 mods.toml 里写 displayTest 是白写——
 *                        fmlloader / fmlcore 的 ModInfo、ModContainer 里
 *                        根本没有这个字符串
 *   1.20.1+ / NeoForge   才轮到 mods.toml 的 displayTest 字段
 * </pre>
 *
 * <p>全程反射：类名稳定，但形态（枚举 → record）与泛型签名各版本有出入，反射就
 * 不用管，也省得为这一件事再多开一套源目录。任何一步找不到就整段放弃——注册不上
 * 顶多是服务器列表里那个兼容标记不准，不值得为它崩。
 */
final class ServerCompat {

    private ServerCompat() {
    }

    /** 在 mod 构造期调用：这时候 ModLoadingContext 才指向我们自己这个容器。 */
    static void ignoreOnServers() {
        try {
            Object ctx = Class.forName("net.minecraftforge.fml.ModLoadingContext")
                    .getMethod("get").invoke(null);
            // 报给服务端的版本号留空 + 对任何远端都点头，就是「别拿我做比对」
            Supplier<String> version = () -> "";
            BiPredicate<String, Boolean> accept = (remote, isServer) -> true;
            Object point;
            Object ext;
            try {
                Class<?> dt = Class.forName(
                        "net.minecraftforge.fml.IExtensionPoint$DisplayTest");
                point = dt;
                ext = dt.getConstructor(Supplier.class, BiPredicate.class)
                        .newInstance(version, accept);
            } catch (Throwable notYet) {
                point = Class.forName("net.minecraftforge.fml.ExtensionPoint")
                        .getField("DISPLAYTEST").get(null);
                ext = Class.forName("org.apache.commons.lang3.tuple.Pair")
                        .getMethod("of", Object.class, Object.class)
                        .invoke(null, version, accept);
            }
            final Object value = ext;
            for (Method m : ctx.getClass().getMethods()) {
                if (m.getName().equals("registerExtensionPoint")
                        && m.getParameterCount() == 2) {
                    m.invoke(ctx, point, (Supplier<Object>) () -> value);
                    return;
                }
            }
        } catch (Throwable ignored) {
            // 注册不上顶多是服务器列表那个兼容标记不准，不值得为它崩
        }
    }
}
