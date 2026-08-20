// ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
package cn.hoshino.pbzh;

import net.minecraft.util.text.ITextComponent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.player.ItemTooltipEvent;
import net.minecraftforge.fml.common.Mod;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

/**
 * Forge 1.15.2 – 1.16.5 的入口。
 *
 * <p>这一版和 1.17+ 那两份最大的不同不在包名，在**运行期的名字空间**：
 * 那个年代的 Minecraft 在游戏里是 SRG 名字——类名是人看得懂的
 * （{@code net.minecraft.util.text.ITextComponent}），但方法名全被换成了
 * {@code func_150261_e} 这种。开发时写 {@code getString()} 能编过，是因为构建
 * 工具最后会把它重映射回去；我们这条路**不重映射**，所以源码里一个 Minecraft
 * 的方法都不能直接调。
 *
 * <p>办法是：**名字由构建期算好，运行期照着反射**。构建脚本把 Mojang 公开的官方
 * 混淆表和 Forge 的 SRG 映射表拿 obf 名联结起来，就能从「官方叫
 * {@code Component#getStyle}」查到「这一版运行期叫 {@code func_150256_b}」，
 * 结果写进 {@code /pbzh/legacy.json}。算不出来就不出包。
 *
 * <p>不按方法形状（返回/参数类型）猜：1.16 的 {@code MutableComponent} 上有两个
 * 都吃 {@code Style} 的方法（setStyle 与 withStyle），按形状挑是碰运气。
 *
 * <p>只有 Forge 自己的东西可以照常写：{@code @Mod}、{@code MinecraftForge.EVENT_BUS}、
 * {@code ItemTooltipEvent#getToolTip} 都是 Forge 的代码，不参与混淆。
 *
 * <p>任何一步找不到就整段放弃——显示层的活儿，宁可不翻也不能把游戏搞崩。
 */
@Mod(LegacyEntry.MODID)
public final class LegacyEntry {
    public static final String MODID = "productivebees_zh_cn";

    private static Constructor<?> newText;
    private static Method getString;
    private static Method getStyle;
    private static Method setStyle;
    private static boolean ready;

    public LegacyEntry() {
        BeeNames.hello("Forge");
        MinecraftForge.EVENT_BUS.addListener(LegacyEntry::onItemTooltip);
        // 名牌是客户端事件，类在服务端不存在，用 try 兜住
        try {
            MinecraftForge.EVENT_BUS.addListener(LegacyEntry::onRenderNameplate);
        } catch (Throwable ignored) {
            // 挂不上顶多是名牌还显示英文
        }
        // 每 tick 一次，但方法自己先比语言表的对象身份，没换过立刻返回。
        // 资源重载后语言表是新对象，那一次才真正去学整合包自己加的蜂名。
        try {
            MinecraftForge.EVENT_BUS.addListener(
                    (net.minecraftforge.event.TickEvent.ClientTickEvent e) ->
                            tick());
        } catch (Throwable ignored) {
            // 注册不上顶多是整合包自定义的蜂名不翻，不能因此让 mod 装不上
        }
        // 「服务端没有这个 mod 也没关系」——这一声明各版本写法不同，统一收在 ServerCompat
        ServerCompat.ignoreOnServers();
    }

    /** 按名字取方法，取不到就返回 null——这一条不成立顶多不翻，不能炸。 */
    private static Method by(Map<String, Map<String, String>> t, String alias,
                             Class<?>... params) {
        try {
            Map<String, String> m = t.get(alias);
            return Class.forName(m.get("owner")).getMethod(m.get("name"), params);
        } catch (Throwable e) {
            return null;
        }
    }

    private static synchronized void init() throws Exception {
        if (ready) {
            return;
        }
        ready = true;
        // 名字表是构建时算的：官方混淆表 ↔ SRG 映射表拿 obf 名一联结，
        // 得到「这一版运行期真正叫什么」。mod 里一个版本相关的名字都不写死。
        Map<String, Map<String, String>> t;
        try (InputStream in = LegacyEntry.class.getResourceAsStream("/pbzh/legacy.json")) {
            if (in == null) {
                return;
            }
            t = new Gson().fromJson(new InputStreamReader(in, StandardCharsets.UTF_8),
                    new TypeToken<Map<String, Map<String, String>>>() { }.getType());
        }
        Class<?> impl = Class.forName(t.get("impl").get("name"));
        newText = impl.getConstructor(String.class);
        getString = by(t, "getString");
        getStyle = by(t, "getStyle");
        Class<?> style = getStyle == null ? null : getStyle.getReturnType();
        setStyle = style == null ? null : by(t, "setStyle", style);
    }

    /** 每 tick 一次；两个方法自己都先比对象身份，没换过立刻返回。 */
    private static void tick() {
        AddonNames.refresh();
        BeeData.refresh();
    }

    static void onItemTooltip(ItemTooltipEvent event) {
        try {
            List<ITextComponent> lines = event.getToolTip();
            if (lines.isEmpty()) {
                return;
            }
            init();
            if (getString == null || newText == null) {
                return;
            }
            for (int i = 0; i < lines.size(); i++) {
                ITextComponent line = lines.get(i);
                String s = (String) getString.invoke(line);
                String zh = BeeNames.translate(s);
                if (zh.equals(s)) {
                    continue;
                }
                Object made = newText.newInstance(zh);
                if (getStyle != null && setStyle != null) {
                    // 原样式带着颜色，丢了就成一行白字，比不翻还扎眼
                    setStyle.invoke(made, getStyle.invoke(line));
                }
                lines.set(i, (ITextComponent) made);
            }
        } catch (Throwable ignored) {
            // 显示层永远不许把游戏搞崩：宁可不翻
        }
    }

    /**
     * 世界里那只蜂头顶的名牌——**显示层**，不碰任何数据。
     *
     * <p>只翻**系统生成名**：当前那串字必须在「模组自己生成的英文名」表里才动手，
     * 玩家用命名牌起的名字原样显示。
     *
     * <p><b>这一段整个走反射，因为同一套源码要编 1.15.2 和 1.16.x 两代，而它们的
     * {@code RenderNameplateEvent} 形状不一样</b>——拿 Forge 官方 jar 核过：
     *
     * <pre>
     *   1.15.2  String getContent()          / setContent(String)
     *   1.16.x  ITextComponent getContent()  / setContent(ITextComponent)
     * </pre>
     *
     * 直接写类型只能过一边（1.15.2 那次构建就是这么红的）。所以读回来什么就认什么：
     * 是 String 就直接用，是组件就走 {@code getString}；写回去按**这一版
     * setContent 真正声明的参数类型**给。
     *
     * <p>新版本那几份还会先按实体类型过滤一道。这一版没有：那两个方法在这个年代都是
     * SRG 名，要为它再引两条映射；而名字表那道闸本身已经够——只有模组自己生成的蜂名
     * 才会命中，何况这里只改渲染出来的字，一个字节的数据都不落。
     */
    static void onRenderNameplate(
            net.minecraftforge.client.event.RenderNameplateEvent event) {
        try {
            init();
            if (newText == null) {
                return;
            }
            Object c = event.getClass().getMethod("getContent").invoke(event);
            if (c == null) {
                return;
            }
            String s;
            if (c instanceof String) {
                s = (String) c;
            } else if (getString != null) {
                s = (String) getString.invoke(c);
            } else {
                return;
            }
            if (!BeeNames.enTable().containsKey(s)) {
                return;                        // 玩家自己起的名字，不碰
            }
            String zh = BeeNames.translate(s);
            if (zh.equals(s)) {
                return;
            }
            Method set = null;
            for (Method m : event.getClass().getMethods()) {
                if (m.getName().equals("setContent") && m.getParameterCount() == 1) {
                    set = m;
                    break;
                }
            }
            if (set == null) {
                return;
            }
            set.invoke(event, set.getParameterTypes()[0] == String.class
                    ? zh : newText.newInstance(zh));
        } catch (Throwable ignored) {
            // 显示层永远不许把游戏搞崩：宁可名牌还是英文
        }
    }
}
