import json
import os
import random
import discord
from discord.ext import commands

# IDs de Roles de Staff Sincronizados
ADMIN_ID = 995843251200327753
DRAGON_ROLE_ID = 1410886251556638860

CONFIG_BOX = {
    "común": {
        "precio": 2500,  # En unidades de cobre (25 PO)
        "limite_diario": 2,
        "pesos": {"Baratijas": 67, "Común": 30, "Poco Común": 2, "Raro": 1}
    },
    "poco común": {
        "precio": 15000,  # En unidades de cobre (150 PO)
        "limite_diario": 2,
        "pesos": {"Común": 65, "Poco Común": 33, "Raro": 2}
    }
}

BANNERS = {
    1: {"nombre": "Fuego de los Dragones", "item_id": "lengua_flamigera", "imagen": "LenguaBanner.png"},
    2: {"nombre": "Movimientos de los Vientos", "item_id": "anillo_evasion", "imagen": "EvasionBanner.png"},
    3: {"nombre": "Misterio sin Precedentes", "item_id": None, "imagen": "NadaBanner.png"}
}


# --- FUNCIONES AUXILIARES INTERNAS ---
def local_cargar_datos():
    if os.path.exists("personajes.json"):
        with open("personajes.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def local_guardar_datos(datos):
    with open("personajes.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)


def local_formatear_monedas(cobre: int) -> str:
    po = cobre // 100
    cobre %= 100
    pp = cobre // 10
    pc = cobre % 10

    partes = []
    if po: partes.append(f"{po} PO")
    if pp: partes.append(f"{pp} PP")
    if pc: partes.append(f"{pc} PC")

    return " ".join(partes) if partes else "0 PC"


def obtener_banner_actual():
    try:
        with open("datos_lichsea.json", "r", encoding="utf-8") as f:
            datos_mundo = json.load(f)
        mes = datos_mundo.get("mes", 1)
        id_banner = ((mes - 1) % 3) + 1
        return BANNERS[id_banner]
    except:
        return BANNERS[3]


def obtener_pools_filtrados():
    if not os.path.exists("tienda_items.json"):
        return {"Baratijas": [], "Común": [], "Poco Común": [], "Raro": []}

    try:
        with open("tienda_items.json", "r", encoding="utf-8") as f:
            tienda = json.load(f)
    except Exception as e:
        print(f"Error al leer tienda_items.json: {e}")
        return {"Baratijas": [], "Común": [], "Poco Común": [], "Raro": []}

    pools = {"Baratijas": [], "Común": [], "Poco Común": [], "Raro": []}

    for info in tienda:
        item_id = info.get("id")
        if not item_id: continue

        # Normalizamos categorías
        cat_lista = [c.lower().strip() for c in info.get("categoria", [])]

        item_limpio = {
            "id": item_id.lower(),
            "nombre": info.get("nombre", "Objeto Desconocido"),
            "descripcion": info.get("descripcion", ""),
            "consumible": info.get("consumible", False)
        }

        # FILTRO EXCLUSIVO (Usa elif para que un item solo entre en UNA bolsa)
        if "raro" in cat_lista:
            pools["Raro"].append(item_limpio)
        elif "poco común" in cat_lista or "poco comun" in cat_lista:
            pools["Poco Común"].append(item_limpio)
        elif "común" in cat_lista or "comun" in cat_lista:
            pools["Común"].append(item_limpio)
        elif "baratijas" in cat_lista or "baratija" in cat_lista:
            pools["Baratijas"].append(item_limpio)

    return pools


def verificar_y_resetear_limites(pj, fecha_id_mundo):
    if "lootboxes" not in pj:
        pj["lootboxes"] = {"común": 0, "poco común": 0, "inventario_cajas": {}}

    if "registro_compras" not in pj["lootboxes"]:
        pj["lootboxes"]["registro_compras"] = {"ultima_fecha": fecha_id_mundo, "común": 0, "poco común": 0}

    if pj["lootboxes"]["registro_compras"]["ultima_fecha"] != fecha_id_mundo:
        pj["lootboxes"]["registro_compras"]["ultima_fecha"] = fecha_id_mundo
        pj["lootboxes"]["registro_compras"]["común"] = 0
        pj["lootboxes"]["registro_compras"]["poco común"] = 0


# ===================== SETUP (ESTILO TIENDA) =====================
def setup(bot: commands.Bot):
    @bot.command(name="tiendalootbox")
    async def tiendalootbox(ctx):
        banner = obtener_banner_actual()

        embed = discord.Embed(
            title="🛒 Tienda de Cajas de Botín",
            description=f"Variedad de cajas disponibles hoy.\n\n**Banner del Mes Activo:** {banner['nombre']}",
            color=discord.Color.gold()
        )

        if banner["item_id"]:
            embed.add_field(
                name="✨ Promoción del Banner",
                value="Si consigues un drop Raro, ¡tienes un 50% de probabilidad de que sea el objeto promocionado de este mes!",
                inline=False
            )

        embed.add_field(
            name="📦 Caja Común",
            value=f"Precio: {local_formatear_monedas(2500)}\nLímite: 2 por día de rol.\nDrops: Baratijas (67%), Común (30%), Poco Común (2%), Raro (1%)",
            inline=False
        )
        embed.add_field(
            name="📦 Caja Poco Común",
            value=f"Precio: {local_formatear_monedas(15000)}\nLímite: 2 por día de rol.\nDrops: Común (65%), Poco Común (33%), Raro (2%)",
            inline=False
        )

        if os.path.exists(banner["imagen"]):
            archivo_imagen = discord.File(banner["imagen"], filename=banner["imagen"])
            embed.set_image(url=f"attachment://{banner['imagen']}")
            return await ctx.send(file=archivo_imagen, embed=embed)

        await ctx.send(embed=embed)

    @bot.command(name="comprarbox")
    async def comprarbox(ctx, alias_pj: str, rareza: str):
        rareza = rareza.lower()
        if rareza not in CONFIG_BOX:
            return await ctx.send("❌ Rareza inválida. Elige entre común o poco común.")

        alias_pj = alias_pj.lower()
        datos = local_cargar_datos()

        pj_encontrado = None
        for uid, info in datos.items():
            if uid == "_historial": continue
            if alias_pj in info.get("personajes", {}):
                pj_encontrado = info["personajes"][alias_pj]
                break

        if not pj_encontrado:
            return await ctx.send("❌ No se encontró ese personaje.")

        if pj_encontrado.get("estado") == "Muerto":
            return await ctx.send("👻 Un personaje muerto no puede comprar cosas.")

        try:
            with open("datos_lichsea.json", "r", encoding="utf-8") as f:
                datos_mundo = json.load(f)
            fecha_id_mundo = f"{datos_mundo.get('dia', 1)}-{datos_mundo.get('mes', 1)}-{datos_mundo.get('año', 1)}"
        except:
            fecha_id_mundo = "1-1-1"

        verificar_y_resetear_limites(pj_encontrado, fecha_id_mundo)

        config = CONFIG_BOX[rareza]
        registro = pj_encontrado["lootboxes"]["registro_compras"]

        if registro[rareza] >= config["limite_diario"]:
            return await ctx.send(
                f"❌ Ya has comprado el límite diario permitido ({config['limite_diario']}) de cajas de rareza {rareza} para este día de rol.")

        if pj_encontrado.get("oro", 0) < config["precio"]:
            saldo_str = local_formatear_monedas(pj_encontrado.get("oro", 0))
            costo_str = local_formatear_monedas(config["precio"])
            return await ctx.send(f"❌ No tienes suficientes monedas. Costo: {costo_str} (Tienes: {saldo_str}).")

        pj_encontrado["oro"] -= config["precio"]
        registro[rareza] += 1

        inv_cajas = pj_encontrado["lootboxes"].setdefault("inventario_cajas", {})
        inv_cajas[rareza] = inv_cajas.get(rareza, 0) + 1

        local_guardar_datos(datos)
        costo_final_str = local_formatear_monedas(config["precio"])
        await ctx.send(
            f"✅ Compra exitosa. Se han descontado {costo_final_str}. Añadida 1 caja de rareza {rareza} a la hoja de **{pj_encontrado['nombre']}**.")

    @bot.command(name="abrirbox")
    async def abrirbox(ctx, alias_pj: str, rareza: str):
        rareza = rareza.lower()
        alias_pj = alias_pj.lower()
        datos = local_cargar_datos()

        pj_encontrado = None
        for uid, info in datos.items():
            if uid == "_historial": continue
            if alias_pj in info.get("personajes", {}):
                pj_encontrado = info["personajes"][alias_pj]
                break

        if not pj_encontrado:
            return await ctx.send("❌ No se encontró ese personaje.")

        inv_cajas = pj_encontrado.get("lootboxes", {}).get("inventario_cajas", {})
        if inv_cajas.get(rareza, 0) <= 0:
            return await ctx.send(f"❌ No tienes cajas de rareza {rareza} para abrir.")

        pools = obtener_pools_filtrados()

        if rareza in CONFIG_BOX:
            config_pesos = CONFIG_BOX[rareza]["pesos"]
            categorias = list(config_pesos.keys())
            pesos = list(config_pesos.values())
            pool_seleccionado = random.choices(categorias, weights=pesos, k=1)[0]
        else:
            pool_seleccionado = rareza.capitalize()

        if pool_seleccionado not in pools or len(pools[pool_seleccionado]) == 0:
            return await ctx.send("❌ La bolsa de premios seleccionada está vacía en este momento.")

        item_ganado = None
        if pool_seleccionado == "Raro":
            banner = obtener_banner_actual()
            if banner["item_id"] and random.random() < 0.50:
                for item in pools["Raro"]:
                    if item["id"] == banner["item_id"].lower():
                        item_ganado = item
                        break

        if not item_ganado:
            item_ganado = random.choice(pools[pool_seleccionado])

        inv_cajas[rareza] -= 1

        if "inventario" not in pj_encontrado:
            pj_encontrado["inventario"] = []

        id_final = item_ganado["id"]
        if id_final == "kit_sanador_consumible":
            pj_encontrado["inventario"].append(f"{id_final} (10)")
        else:
            pj_encontrado["inventario"].append(id_final)

        local_guardar_datos(datos)

        msg = f"📦 Abriendo caja {rareza} de **{pj_encontrado['nombre']}**...\n\n¡Obtuviste un objeto de categoría **{pool_seleccionado}**!\n"
        msg += f"✨ **Objeto:** {item_ganado['nombre']}\n📝 *Descripción:* {item_ganado['descripcion']}"
        await ctx.send(msg)

    @bot.command(name="darbox")
    async def darbox(ctx, alias_pj: str, rareza: str, cantidad: int = 1):
        es_staff = ctx.author.id == ADMIN_ID or any(rol.id == DRAGON_ROLE_ID for rol in ctx.author.roles)
        if not es_staff:
            return await ctx.send("❌ No tienes permiso para usar este comando.")

        if cantidad <= 0:
            return await ctx.send("❌ Cantidad inválida.")

        rareza = rareza.lower()
        alias_pj = alias_pj.lower()
        datos = local_cargar_datos()

        # =========================================================================
        # MODO MASIVO: Regalar cajas a TODOS los personajes vivos
        # =========================================================================
        if alias_pj == "all_characters":
            total_pjs_beneficiados = 0

            for uid, info in datos.items():
                # Validación Blindada: Si no es un diccionario o no contiene la clave 'personajes',
                # saltamos de inmediato. Esto ignora _historial, configuraciones o cualquier otra cosa.
                if not isinstance(info, dict) or "personajes" not in info:
                    continue

                # Procesamos de forma segura los personajes del usuario
                for alias, pj in info["personajes"].items():
                    # Comprobamos estrictamente que el estado sea "Vivo"
                    # Usamos .get("estado", "Vivo") por si algún PJ viejo no tiene la clave en su JSON
                    if pj.get("estado", "Vivo") == "Vivo":

                        # Aseguramos la inicialización de la estructura de lootboxes
                        if "lootboxes" not in pj:
                            pj["lootboxes"] = {"común": 0, "poco común": 0, "inventario_cajas": {}}

                        inv_cajas = pj["lootboxes"].setdefault("inventario_cajas", {})
                        inv_cajas[rareza] = inv_cajas.get(rareza, 0) + cantidad
                        total_pjs_beneficiados += 1

            if total_pjs_beneficiados == 0:
                return await ctx.send("⚠️ No se encontraron personajes vivos en el sistema para repartir cajas.")

            local_guardar_datos(datos)
            return await ctx.send(
                f"🎉 **¡REPARTO MASIVO EXITOSO!**\nSe han repartido **{cantidad}** cajas de rareza **{rareza}** "
                f"a todos los personajes vivos del servidor (Total de beneficiados: **{total_pjs_beneficiados}** PJs)."
            )

        # =========================================================================
        # MODO INDIVIDUAL: Funciona exacta
        # =========================================================================
        pj_encontrado = None
        for uid, info in datos.items():
            if uid == "_historial": continue
            if alias_pj in info.get("personajes", {}):
                pj_encontrado = info["personajes"][alias_pj]
                break

        if not pj_encontrado:
            return await ctx.send("❌ No se encontró ese personaje.")

        if "lootboxes" not in pj_encontrado:
            pj_encontrado["lootboxes"] = {"común": 0, "poco común": 0, "inventario_cajas": {}}

        inv_cajas = pj_encontrado["lootboxes"].setdefault("inventario_cajas", {})
        inv_cajas[rareza] = inv_cajas.get(rareza, 0) + cantidad

        local_guardar_datos(datos)
        await ctx.send(
            f"✅ Se han añadido {cantidad} cajas de rareza {rareza} al inventario de cajas de **{pj_encontrado['nombre']}**."
        )

    @bot.command(name="revisardrops")
    async def revisardrops(ctx, pool_name: str = None):
        es_staff = ctx.author.id == ADMIN_ID or any(rol.id == DRAGON_ROLE_ID for rol in ctx.author.roles)
        if not es_staff:
            return await ctx.send("❌ No tienes permiso para usar este comando.")

        pools = obtener_pools_filtrados()
        if pool_name:
            pool_name = pool_name.capitalize()
            if pool_name in ["Poco común", "Poco comun"]:
                pool_name = "Poco Común"

            if pool_name not in pools:
                return await ctx.send("❌ Pool no válido. Usa: Baratijas, Común, Poco Común o Raro.")
            items = pools[pool_name]
            lista_txt = f"📦 Items en pool {pool_name} ({len(items)} detectados):\n"
            lista_txt += ", ".join([f"{i['nombre']} (`{i['id']}`)" for i in items[:40]])
            if len(items) > 40:
                lista_txt += "... y más."
            await ctx.send(lista_txt[:2000])
        else:
            resumen = "📋 Resumen de ítems cargados en el sistema de cajas:\n"
            for k, v in pools.items():
                resumen += f"- Pool [{k}]: {len(v)} ítems válidos.\n"
            await ctx.send(resumen)
