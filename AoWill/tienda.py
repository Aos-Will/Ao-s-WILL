import json
import os
import discord
from discord.ext import commands

ARCHIVO_DATOS = "personajes.json"
ARCHIVO_ITEMS = "tienda_items.json"

ADMIN_ID = 995843251200327753
DRAGON_ROLE_ID = 1410886251556638860
# ================================================================
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

        for item in items_pagina:
            categorias = item.get("categoria", [])
            lista_rarezas = ["Común", "Poco Común", "Raro", "Muy Raro", "Legendario"]
            rareza_detectada = "Común"  # Por defecto

            for cat in categorias:
                if cat in lista_rarezas:
                    rareza_detectada = cat
                    break

            # 2. Formatear Stock
            stock_val = item.get("stock")
            stock_txt = f"**{stock_val}**" if stock_val is not None else "♾️"

            precio_txt = formatear_monedas(item.get("precio", 0))

            embed.add_field(
                name=f"{item['nombre']} (`{item['id']}`)",
                value=(
                    f"💰 **Precio:** {precio_txt} | 📦 **Stock:** {stock_txt}\n"
                    f"✨ **Rareza:** {rareza_detectada}\n"
                    f"📝 {item.get('descripcion', 'Sin descripción.')}"
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

    # ---------- COMPRAR y Usar ----------

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

