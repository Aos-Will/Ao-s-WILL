import json
import os
import discord
import asyncio
from discord.ext import commands
# Carga el .jsom de tienda y personajes.json
ARCHIVO_DATOS = "personajes.json"
ARCHIVO_ITEMS = "tienda_items.json"

ADMIN_ID = 995843251200327753
DRAGON_ROLE_ID = 1410886251556638860

## Almacena temporalmemte la funcion !trade entre jugadores.
TRADES_PENDIENTES = {}

# ===================== CARGAR / GUARDAR =====================
def cargar_datos():
    if not os.path.exists(ARCHIVO_DATOS):
        return {}
    with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_datos(datos):
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


def cargar_items():
    if not os.path.exists(ARCHIVO_ITEMS):
        return []
    with open(ARCHIVO_ITEMS, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_items(items):
    with open(ARCHIVO_ITEMS, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=4, ensure_ascii=False)

def obtener_fecha_mundo():
    try:
        with open("datos_lichsea.json", "r", encoding="utf-8") as f:
            datos = json.load(f)
            return {

                "dia": datos.get("dia", 1),

                "mes": datos.get("mes", 1),

                "año": datos.get("año", 1)

            }
    except:
        return {"dia": 1, "mes": 1, "año": 1}

# ===================== MONEDAS =====================
def formatear_monedas(cobre: int) -> str:
    po = cobre // 100
    cobre %= 100
    pp = cobre // 10
    pc = cobre % 10

    partes = []
    if po:
        partes.append(f"{po} PO")
    if pp:
        partes.append(f"{pp} PP")
    if pc:
        partes.append(f"{pc} PC")

    return " ".join(partes) if partes else "0 PC"


# ===================== VIEW PAGINADA =====================
class TiendaView(discord.ui.View):
    def __init__(self, items):
        super().__init__(timeout=120)
        self.items = items
        self.pagina = 0
        self.items_por_pagina = 5

    def crear_embed(self):
        inicio = self.pagina * self.items_por_pagina
        fin = inicio + self.items_por_pagina
        items_pagina = self.items[inicio:fin]

        embed = discord.Embed(
            title="🛒 Catálogo de la Tienda",
            color=discord.Color.gold()
        )

        # Mantenemos tu lista, pero la usaremos comparando en minúsculas
        lista_rarezas = ["común", "poco común", "raro", "muy raro", "legendario"]

        for item in items_pagina:
            categorias = item.get("categoria", [])
            rareza_detectada = "Común"

            for cat in categorias:
                # Comparamos todo en minúsculas para que sea insensible a mayúsculas/tildes
                if cat.lower() in lista_rarezas:
                    rareza_detectada = cat # Esto toma el nombre tal cual viene del JSON
                    break

            stock_val = item.get("stock")
            stock_txt = f"**{stock_val}**" if stock_val is not None else "♾️"
            precio_txt = formatear_monedas(item.get("precio", 0))

            # --- Lógica de truncado ---
            descripcion = item.get('descripcion', 'Sin descripción.')
            if len(descripcion) > 100:
                descripcion = descripcion[:97] + "..."
            # --------------------------

            embed.add_field(
                name=f"{item['nombre']} (`{item['id']}`)",
                value=(
                    f"💰 **Precio:** {precio_txt} | 📦 **Stock:** {stock_txt}\n"
                    f"✨ **Rareza:** {rareza_detectada}\n"
                    f"📝 {descripcion}"
                ),
                inline=False
            )

        total_paginas = (len(self.items) - 1) // self.items_por_pagina + 1
        embed.set_footer(text=f"Página {self.pagina + 1}/{total_paginas}")
        return embed

    @discord.ui.button(label="◀", style=discord.ButtonStyle.gray)
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.pagina > 0: self.pagina -= 1
        await interaction.response.edit_message(embed=self.crear_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.gray)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_paginas = (len(self.items) - 1) // self.items_por_pagina
        if self.pagina < total_paginas: self.pagina += 1
        await interaction.response.edit_message(embed=self.crear_embed(), view=self)

# ===================== SETUP =====================
def setup(bot: commands.Bot):
    # ---------- VER TIENDA ----------
    @bot.command()
    async def tienda(ctx, *, categoria: str = None):
        items_raw = cargar_items()
        if not items_raw:
            await ctx.send("La tienda está vacía.")
            return

        items = [i for i in items_raw if i.get("stock") != 0]

        if not items:
            await ctx.send("❌ Actualmente todos los objetos están agotados.")
            return

        if categoria:
            categoria_buscada = categoria.lower().strip()
            items_filtrados = []
            for i in items:
                cat_item = i.get("categoria", "")
                if isinstance(cat_item, list):
                    if categoria_buscada in [c.lower() for c in cat_item]:
                        items_filtrados.append(i)
                elif str(cat_item).lower() == categoria_buscada:
                    items_filtrados.append(i)

            if not items_filtrados:
                await ctx.send(f"No encontré la categoría `{categoria}` con stock. Mostrando todo:")
                items_mostrar = items
            else:
                items_mostrar = items_filtrados
        else:
            items_mostrar = items

        view = TiendaView(items_mostrar)
        await ctx.send(embed=view.crear_embed(), view=view)

    # ---------- SISTEMA DE ENTRENAMIENTO ----------
    @bot.command()
    async def entrenar(ctx, alias: str, *, tipo_entrenamiento: str = None):
        alias = alias.lower()
        datos = cargar_datos()
        uid = str(ctx.author.id)
        pj = datos.get(uid, {}).get("personajes", {}).get(alias)

        if not pj:
            await ctx.send("❌ No tienes ese personaje registrado o no te pertenece.")
            return

        if pj.get("estado") == "Muerto":
            await ctx.send(f"❌ **{pj['nombre']}** está muerto. Los muertos no entrenan.")
            return

        cal = obtener_fecha_mundo()
        fecha_actual_tupla = (cal["año"], cal["mes"], cal["dia"])

        # --- LÓGICA DE COOLDOWNS SEPARADOS ---
        for key in ["cooldown_alimentacion", "cooldown_tecnico"]:
            cd = pj.get(key)
            if cd:
                if fecha_actual_tupla >= (cd["año"], cd["mes"], cd["dia"]):
                    pj[key] = None

        # Opciones disponibles
        opciones = {
            "buena alimentacion": {"nombre": "Buena alimentación y entrenamiento", "costo": 2000, "tipo": "ali"},
            "alimentacion": {"nombre": "Buena alimentación y entrenamiento", "costo": 2000, "tipo": "ali"},
            "concentrado": {"nombre": "Entrenamiento concentrado", "costo": 2000, "tipo": "tec"},
            "especializado": {"nombre": "Entrenamiento especializado", "costo": 2000, "tipo": "tec"},
            "los 3 grandes": {"nombre": "Los 3 Grandes", "costo": 120000, "tipo": "dote"},
            "3 grandes": {"nombre": "Los 3 Grandes", "costo": 120000, "tipo": "dote"}
        }

        if not tipo_entrenamiento:
            opcion_valida = False
        else:
            entrada_usuario = tipo_entrenamiento.lower().strip()
            clave_encontrada = next((k for k in opciones if k in entrada_usuario), None)
            opcion_valida = clave_encontrada is not None

        if not opcion_valida:
            await ctx.send(
                f"📋 **Opciones de Entrenamiento para {pj['nombre']}:**\n"
                f"💡 *Escribe el comando seguido de una de estas opciones exactas:*\n\n"
                f"1️⃣ `!entrenar {alias} alimentacion` — Costo: 20 PO\n"
                f"   └ Estado de 'Descansado' por la partida.\n"
                f"2️⃣ `!entrenar {alias} concentrado` — Costo: 20 PO\n"
                f"   └ Obtienes +4 a una prueba de habilidad a tu elección por toda la partida.\n"
                f"3️⃣ `!entrenar {alias} especializado` — Costo: 20 PO\n"
                f"   └ Obtienes +2 a una estadística a tu elección por toda la partida.\n"
                f"4️⃣ `!entrenar {alias} los 3 grandes` — Costo: 1200 Oro (120,000 PC)\n"
                f"   └ Obtienes la dote permanente 'Los 3 grandes'.\n\n"
                f"⚠️ *'Pueden elegir el Entrenamiento Concentrado o el Entrenamiento Especializado. Pero ojo: es uno o el otro. No pueden quedarse con ambos, y mucho menos intentar repetir el mismo proceso durante la misma misión. En el mundo de la hechicería, solo tienes una oportunidad para definir tu camino.'*"
            )
            return

        # 3. PROCESAMIENTO
        datos_opcion = opciones[clave_encontrada]
        nombre_entrenamiento = datos_opcion["nombre"]
        costo_cobre = datos_opcion["costo"]
        categoria = datos_opcion["tipo"]

        # Validación de Cooldown según categoría
        if categoria == "ali" and pj.get("cooldown_alimentacion"):
            await ctx.send(f"❌ **{pj['nombre']}** ya tiene activa la 'Buena alimentación'.")
            return
        if categoria == "tec" and pj.get("cooldown_tecnico"):
            cd = pj["cooldown_tecnico"]
            await ctx.send(f"❌ **{pj['nombre']}** ya tiene un entrenamiento técnico activo: **{cd['tipo']}**.")
            return

        if pj.get("oro", 0) < costo_cobre:
            await ctx.send(f"❌ **{pj['nombre']}** no tiene suficiente oro. Requiere: {formatear_monedas(costo_cobre)}")
            return

        # Calcular fecha
        d, m, a = cal["dia"] + 2, cal["mes"], cal["año"]
        while d > 30: d -= 30; m += 1
        while m > 12: m -= 12; a += 1

        pj["oro"] -= costo_cobre

        if categoria == "dote":
            if "inventario" not in pj: pj["inventario"] = []
            if "Dote: Los 3 Grandes" not in pj["inventario"]:
                pj["inventario"].append("Dote: Los 3 Grandes")
            await ctx.send(
                f"✨ **{pj['nombre']}** ha pagado {formatear_monedas(costo_cobre)}.\n🏅 Ha obtenido la dote: **'Los 3 Grandes'**.")
        else:
            key = "cooldown_alimentacion" if categoria == "ali" else "cooldown_tecnico"
            pj[key] = {"dia": d, "mes": m, "año": a, "tipo": nombre_entrenamiento}
            await ctx.send(
                f"💪 **{pj['nombre']}** ha pagado {formatear_monedas(costo_cobre)} e inició: **{nombre_entrenamiento}**.\n"
                f"📝 *Recuerda declarar en el Hilo que usaste este entrenamiento.*\n"
                f"⏳ Los efectos terminan el día **{d}/{m}/{a}**."
            )

        guardar_datos(datos)


    # ---------- Inventario -------------- #
    @bot.command(aliases=["inv", "Inventario"])
    async def inventario(ctx, alias: str):
        alias = alias.lower()
        datos = cargar_datos()
        personaje_encontrado = None

        for uid, info in datos.items():
            if uid == "_historial": continue
            pj = info.get("personajes", {}).get(alias)
            if pj:
                personaje_encontrado = pj
                break

        if not personaje_encontrado:
            await ctx.send(f"No encontré al personaje con alias: **{alias}**", delete_after=60)
            return

        nombre = personaje_encontrado.get("nombre", alias.capitalize())
        inv_ids = personaje_encontrado.get("inventario", [])
        oro = personaje_encontrado.get("oro", 0)

        lista_objetos = "\n".join([f"• {item_id}" for item_id in inv_ids]) if inv_ids else "*El inventario está vacío.*"

        embed = discord.Embed(
            title=f"🎒 Inventario de {nombre}",
            color=discord.Color.blue(),
            description=f"**Riqueza:** {formatear_monedas(oro)}\n\n**Objetos:**\n{lista_objetos}"
        )
        embed.set_footer(text="Este mensaje se eliminará en 5 minutos.")
        await ctx.send(embed=embed, delete_after=300)
        try:
            await ctx.message.delete()
        except:
            pass

    @bot.command(aliases=["item", "objeto"])
    async def ver(ctx, item_id: str):
        item_id = item_id.lower()
        items = cargar_items()
        item = next((i for i in items if i["id"] == item_id), None)

        if not item:
            await ctx.send(f"No encontré ningún objeto con el ID: {item_id}")
            return

        embed = discord.Embed(
            title=item['nombre'],
            description=item.get("descripcion", "Sin descripción."),
            color=discord.Color.blue()
        )
        embed.add_field(name="Precio", value=formatear_monedas(item['precio']), inline=True)

        cat = item.get("categoria", "General")
        cat_txt = ", ".join(cat) if isinstance(cat, list) else cat
        embed.add_field(name="Categoría", value=cat_txt, inline=True)

        stock_val = item.get("stock", "Infinito")
        embed.add_field(name="Stock", value=str(stock_val) if stock_val is not None else "Infinito", inline=True)

        es_consumible = "Sí" if item.get("consumible") else "No"
        embed.add_field(name="Consumible", value=es_consumible, inline=True)
        embed.set_footer(text=f"ID: {item['id']}")
        await ctx.send(embed=embed)

     # ---------- VENDER A LA TIENDA (1/5 del precio original) ----------
    @bot.command()
    async def vender(ctx, alias: str, item_id: str):
        alias = alias.lower()
        item_id = item_id.lower()

        datos = cargar_datos()
        uid = str(ctx.author.id)
        pj = datos.get(uid, {}).get("personajes", {}).get(alias)

        if not pj:
            await ctx.send("❌ No tienes ese personaje registrado o no te pertenece.")
            return

        inventario = pj.get("inventario", [])
        item_en_inv = next((x for x in inventario if x.lower().startswith(item_id)), None)

        if not item_en_inv:
            await ctx.send(f"❌ **{pj['nombre']}** no tiene el objeto `{item_id}` en su inventario.")
            return

        items_tienda = cargar_items()
        item_base = next((i for i in items_tienda if i["id"] == item_id), None)

        if not item_base:
            await ctx.send("❌ Ese objeto no se puede vender a la tienda porque es un objeto único/Lore.")
            return

        precio_original = item_base.get("precio", 0)
        if precio_original <= 0:
            await ctx.send("❌ Este objeto no tiene valor comercial.")
            return

        pago_cobre = precio_original // 5
        if pago_cobre < 1:
            pago_cobre = 1

        inventario.remove(item_en_inv)
        pj["oro"] = pj.get("oro", 0) + pago_cobre
        guardar_datos(datos)

        if item_base.get("stock") is not None:
            item_base["stock"] += 1
            guardar_items(items_tienda)

        await ctx.send(
            f"💰 **{pj['nombre']}** ha vendido **{item_base['nombre']}** a la tienda.\n"
            f"   └ **Precio original:** {formatear_monedas(precio_original)}\n"
            f"   └ **Recibido (1/5):** {formatear_monedas(pago_cobre)}"
        )

    # ---------- INICIAR INTERCAMBIO ENTRE JUGADORES ----------
    @bot.command()
    async def trade(ctx, item_id: str, mi_pj_alias: str, target_pj_alias: str, precio_po: int):
        mi_pj_alias = mi_pj_alias.lower()
        target_pj_alias = target_pj_alias.lower()
        item_id = item_id.lower()

        if precio_po < 0:
            await ctx.send("❌ El precio de venta no puede ser negativo.")
            return

        datos = cargar_datos()
        uid_vendedor = str(ctx.author.id)
        pj_vendedor = datos.get(uid_vendedor, {}).get("personajes", {}).get(mi_pj_alias)

        if not pj_vendedor:
            await ctx.send("❌ No posees el personaje vendedor indicado.")
            return

        inventario_vendedor = pj_vendedor.get("inventario", [])
        item_en_inv = next((x for x in inventario_vendedor if x.lower().startswith(item_id)), None)
        if not item_en_inv:
            await ctx.send(f"❌ **{pj_vendedor['nombre']}** no tiene `{item_id}` en su inventario.")
            return

        pj_comprador = None
        uid_comprador = None
        for uid_busqueda, info in datos.items():
            if uid_busqueda == "_historial": continue
            if target_pj_alias in info.get("personajes", {}):
                pj_comprador = info["personajes"][target_pj_alias]
                uid_comprador = uid_busqueda
                break

        if not pj_comprador:
            await ctx.send(f"❌ No se encontró al personaje objetivo: **{target_pj_alias}**.")
            return

        if mi_pj_alias == target_pj_alias:
            await ctx.send("❌ No puedes hacer un trade contigo mismo.")
            return

        items_tienda = cargar_items()
        item_base = next((i for i in items_tienda if i["id"] == item_id), None)

        precio_tienda_original = item_base.get("precio", 0) if item_base else 0
        impuesto_cobre = int(precio_tienda_original * 0.20)

        if pj_vendedor.get("oro", 0) < impuesto_cobre:
            await ctx.send(
                f"❌ **{pj_vendedor['nombre']}** no tiene suficiente oro para pagar el impuesto de aduana del 20%.\n"
                f"   └ **Impuesto requerido:** {formatear_monedas(impuesto_cobre)}"
            )
            return

        precio_venta_cobre = precio_po * 100
        trade_id = f"{mi_pj_alias}_{target_pj_alias}"

        TRADES_PENDIENTES[trade_id] = {
            "vendedor_uid": uid_vendedor,
            "vendedor_alias": mi_pj_alias,
            "comprador_uid": uid_comprador,
            "comprador_alias": target_pj_alias,
            "item_en_inv": item_en_inv,
            "precio_venta": precio_venta_cobre,
            "impuesto": impuesto_cobre,
            "activo": True
        }

        await ctx.send(
            f"🤝 **¡Propuesta de Intercambio Enviada!**\n"
            f"🔹 **De:** {pj_vendedor['nombre']} ({ctx.author.mention})\n"
            f"🔹 **Para:** {pj_comprador['nombre']}\n"
            f"📦 **Objeto:** `{item_en_inv}`\n"
            f"💰 **Precio de venta:** {formatear_monedas(precio_venta_cobre)} ({precio_po} PO)\n"
            f"⚖️ **Impuesto de envío cobrado al vendedor:** {formatear_monedas(impuesto_cobre)}\n\n"
            f"Para aceptar, el comprador debe escribir antes de 2 minutos:\n"
            f"`!trade_accept {mi_pj_alias} {target_pj_alias}`"
        )

        await asyncio.sleep(120)
        if trade_id in TRADES_PENDIENTES and TRADES_PENDIENTES[trade_id]["activo"]:
            del TRADES_PENDIENTES[trade_id]
            await ctx.send(f"⏳ El intercambio entre **{mi_pj_alias}** y **{target_pj_alias}** ha expirado.")

    # ---------- ACEPTAR EL INTERCAMBIO ----------
    @bot.command(name="trade_accept")
    async def trade_accept(ctx, vendedor_alias: str, mi_pj_alias: str):
        vendedor_alias = vendedor_alias.lower()
        mi_pj_alias = mi_pj_alias.lower()
        trade_id = f"{vendedor_alias}_{mi_pj_alias}"

        if trade_id not in TRADES_PENDIENTES:
            await ctx.send("❌ No existe ningún intercambio activo con esos parámetros o ya expiró.")
            return

        trade = TRADES_PENDIENTES[trade_id]
        datos = cargar_datos()
        uid_comprador_real = str(ctx.author.id)

        if trade["comprador_uid"] != uid_comprador_real:
            await ctx.send("❌ No tienes permiso para aceptar este intercambio. No eres el dueño del personaje receptor.")
            return

        pj_vendedor = datos.get(trade["vendedor_uid"], {}).get("personajes", {}).get(vendedor_alias)
        pj_comprador = datos.get(trade["comprador_uid"], {}).get("personajes", {}).get(mi_pj_alias)

        if not pj_vendedor or not pj_comprador:
            await ctx.send("❌ Error crítico: Uno de los personajes involucrados ya no existe.")
            del TRADES_PENDIENTES[trade_id]
            return

        if pj_comprador.get("oro", 0) < trade["precio_venta"]:
            await ctx.send(f"❌ **{pj_comprador['nombre']}** no tiene suficiente dinero. Requiere {formatear_monedas(trade['precio_venta'])}.")
            return

        inventario_vendedor = pj_vendedor.get("inventario", [])
        if trade["item_en_inv"] not in inventario_vendedor:
            await ctx.send("❌ El vendedor ya no posee el objeto en su inventario.")
            del TRADES_PENDIENTES[trade_id]
            return

        trade["activo"] = False

        pj_vendedor["oro"] -= trade["impuesto"]
        pj_comprador["oro"] -= trade["precio_venta"]
        pj_vendedor["oro"] += trade["precio_venta"]

        inventario_vendedor.remove(trade["item_en_inv"])
        if "inventario" not in pj_comprador:
            pj_comprador["inventario"] = []
        pj_comprador["inventario"].append(trade["item_en_inv"])

        guardar_datos(datos)
        del TRADES_PENDIENTES[trade_id]

        await ctx.send(
            f"✅ **¡Intercambio Completado con Éxito!**\n"
            f"📦 **{pj_comprador['nombre']}** recibió: `{trade['item_en_inv']}`\n"
            f"💸 **Pago realizado:** {formatear_monedas(trade['precio_venta'])}\n"
            f"⚖️ **Impuesto de aduana cobrado a {pj_vendedor['nombre']}:** {formatear_monedas(trade['impuesto'])}"
        )





    # ---------- COMPRAR y Usar ----------#

    @bot.command()
    async def dar_objeto(ctx, alias: str, *, item_id: str):
        # Usamos las variables definidas al inicio del archivo
        es_staff = ctx.author.id == ADMIN_ID or any(rol.id == DRAGON_ROLE_ID for rol in ctx.author.roles)

        if not es_staff:
            await ctx.send("No tienes permiso para usar este comando.")
            return

        alias = alias.lower()
        datos = cargar_datos()

        # Intentamos cargar items (asegúrate de tener definida cargar_items() en tu script)
        try:
            items_tienda = cargar_items()
        except:
            items_tienda = []

        encontrado = False

        # Buscamos en toda la base de datos quién tiene ese alias
        for uid, info in datos.items():
            if uid == "_historial":
                continue

            personajes = info.get("personajes", {})
            if alias in personajes:
                pj = personajes[alias]
                if "inventario" not in pj:
                    pj["inventario"] = []

                # Si el objeto está en el JSON, usamos su ID. Si no, usamos el texto que escribiste.
                item_base = next((i for i in items_tienda if i["id"].lower() == item_id.lower()), None)

                if item_base:
                    pj["inventario"].append(item_base["id"])
                    nombre_msg = item_base["nombre"]
                else:
                    # Es un objeto de Lore/Inventado
                    pj["inventario"].append(item_id)
                    nombre_msg = item_id

                guardar_datos(datos)
                await ctx.send(f"✅ Se ha entregado **{nombre_msg}** a **{pj['nombre']}**.")
                encontrado = True
                break

        if not encontrado:
            await ctx.send(f"❌ No encontré a ningún personaje con el alias `{alias}`.")

    @bot.command()
    async def comprar(ctx, alias: str, item_id: str):
        alias = alias.lower()
        item_id = item_id.lower()

        items_tienda = cargar_items()
        item = next((i for i in items_tienda if i["id"] == item_id), None)

        if not item:
            await ctx.send("Ese objeto no existe en la tienda.")
            return

        datos = cargar_datos()
        uid = str(ctx.author.id)
        pj = datos.get(uid, {}).get("personajes", {}).get(alias)

        if not pj:
            await ctx.send("No tienes ese personaje.")
            return

        # --- LÓGICA DE CATEGORÍAS Y COOLDOWN ---
        categorias = [c.lower() for c in item.get("categoria", [])]
        rarezas_esp = ["poco común", "raro", "muy raro", "legendario"]

        # Es especial si tiene una rareza y NO es consumible
        es_especial = any(r in categorias for r in rarezas_esp)
        es_consumible = item.get("consumible", False)

        # CORRECCIÓN: Solo verificamos cooldown si el objeto ACTUAL es especial
        if es_especial and not es_consumible:
            cal = obtener_fecha_mundo()
            cd_compra = pj.get("cooldown_compra")

            if cd_compra:
                # Comparamos con la fecha del mundo de Lichsea
                if (cal["año"], cal["mes"], cal["dia"]) < (cd_compra["año"], cd_compra["mes"], cd_compra["dia"]):
                    fecha_libre = f"{cd_compra['dia']}/{cd_compra['mes']}/{cd_compra['año']}"
                    await ctx.send(
                        f"❌ **{pj['nombre']}** tiene un cooldown activo hasta el {fecha_libre} para objetos especiales.")
                    return
                else:
                    # El cooldown ya pasó, lo limpiamos
                    pj["cooldown_compra"] = None

        # --- DINERO Y STOCK ---
        precio_item = item.get("precio", 0)
        if pj.get("oro", 0) < precio_item:
            await ctx.send(f"No tienes suficiente oro. Necesitas {precio_item} po.")
            return

        if item.get("stock") is not None:
            if item["stock"] <= 0:
                await ctx.send("Este objeto está agotado.")
                return
            item["stock"] -= 1
            guardar_items(items_tienda)

        # --- PROCESAMIENTO DE COMPRA ---
        pj["oro"] -= precio_item
        if "inventario" not in pj: pj["inventario"] = []

        # Si es kit, lo guardamos con sus usos
        if item_id == "kit_sanador_consumible":
            pj["inventario"].append(f"{item_id} (10)")
        else:
            pj["inventario"].append(item_id)

        # --- ACTIVACIÓN DE COOLDOWN ---
        msg_extra = ""
        if not es_consumible and es_especial:
            cal = obtener_fecha_mundo()
            # Sumamos 14 días (puedes ajustar este valor)
            d, m, a = cal["dia"] + 14, cal["mes"], cal["año"]
            while d > 30:  # Meses de 30 días en Lichsea
                d -= 30
                m += 1
            while m > 12:
                m -= 12
                a += 1
            pj["cooldown_compra"] = {"dia": d, "mes": m, "año": a}
            msg_extra = f"\n⚠️ **Cooldown activado:** No puedes comprar más objetos especiales hasta el {d}/{m}/{a}."

        guardar_datos(datos)
        await ctx.send(f"✅ **{pj['nombre']}** ha comprado **{item['nombre']}**.{msg_extra}")

    @bot.command()
    async def usar(ctx, alias: str, item_id: str):
        alias, item_id = alias.lower(), item_id.lower()
        datos = cargar_datos()

        try:
            items_tienda = cargar_items()
        except:
            items_tienda = []

        uid = str(ctx.author.id)
        pj = datos.get(uid, {}).get("personajes", {}).get(alias)

        if not pj:
            await ctx.send("No tienes ese personaje.")
            return

        inventario = pj.get("inventario", [])
        # Buscamos coincidencias en el inventario
        item_en_inv = next((x for x in inventario if x.lower().startswith(item_id)), None)

        if not item_en_inv:
            await ctx.send(f"No tienes el objeto `{item_id}` en tu inventario.")
            return

        item_base = next((i for i in items_tienda if i["id"].lower() == item_id), None)

        # Si el objeto NO está en el JSON (es de Lore)
        if not item_base:
            await ctx.send(f"✨ **{pj['nombre']}** utiliza **{item_en_inv}**.")
            return

        # Si es el Kit Sanador (Lógica de cargas)
        if item_id == "kit_sanador_consumible":
            usos = 10
            if "(" in item_en_inv:
                try:
                    usos = int(item_en_inv.split("(")[1].split(")")[0])
                except:
                    usos = 10
            nuevo_uso = usos - 1
            inventario.remove(item_en_inv)
            if nuevo_uso > 0:
                inventario.append(f"{item_id} ({nuevo_uso})")
                await ctx.send(f"**{pj['nombre']}** usa el kit. Quedan {nuevo_uso} usos.")
            else:
                await ctx.send(f"**{pj['nombre']}** ha agotado el kit sanador.")
            guardar_datos(datos)
            return

        # Si es un objeto del JSON normal
        await ctx.send(f"**{pj['nombre']}** usa **{item_base['nombre']}**.")
        if item_base.get("consumible", False):
            if item_en_inv in inventario:
                inventario.remove(item_en_inv)
                await ctx.send(f"El objeto **{item_base['nombre']}** se ha consumido.")

        guardar_datos(datos)

