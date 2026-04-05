import json
import os
import discord
from discord.ext import commands

ARCHIVO_DATOS = "personajes.json"
ARCHIVO_ITEMS = "tienda_items.json"


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
            title="🛒 Tienda",
            color=discord.Color.gold()
        )

        for item in items_pagina:
            embed.add_field(
                name=f"{item['nombre']} ({item['id']})",
                value=f"Precio: {formatear_monedas(item['precio'])}\n{item['descripcion']}",
                inline=False
            )

        total_paginas = (len(self.items) - 1) // self.items_por_pagina + 1
        embed.set_footer(text=f"Página {self.pagina + 1}/{total_paginas}")

        return embed

    @discord.ui.button(label="◀", style=discord.ButtonStyle.gray)
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.pagina > 0:
            self.pagina -= 1

        await interaction.response.edit_message(
            embed=self.crear_embed(),
            view=self
        )

    @discord.ui.button(label="▶", style=discord.ButtonStyle.gray)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):

        total_paginas = (len(self.items) - 1) // self.items_por_pagina

        if self.pagina < total_paginas:
            self.pagina += 1

        await interaction.response.edit_message(
            embed=self.crear_embed(),
            view=self
        )


# ===================== SETUP =====================
def setup(bot: commands.Bot):

    # ---------- VER TIENDA ----------
    @bot.command()
    async def tienda(ctx, categoria: str = None):
        items = cargar_items()

        if not items:
            await ctx.send("La tienda está vacía.")
            return


        if categoria:
            categoria_buscada = categoria.lower()
            items_filtrados = []

            for i in items:
                cat_item = i.get("categoria", "")
                if isinstance(cat_item, list):
                    if categoria_buscada in [c.lower() for c in cat_item]:
                        items_filtrados.append(i)
                elif cat_item.lower() == categoria_buscada:
                    items_filtrados.append(i)

            if not items_filtrados:
                await ctx.send(f"No encontré la categoría `{categoria}`. Mostrando toda la tienda:")
                items_mostrar = items
            else:
                items_mostrar = items_filtrados
        else:
            # Exepción para mostrar TODO
            items_mostrar = items

        view = TiendaView(items_mostrar)
        await ctx.send(
            embed=view.crear_embed(),
            view=view
        )

    # ---------- Inventario -------------- #
    @bot.command(aliases=["inv", "Inventario"])
    async def inventario(ctx, alias: str):
        alias = alias.lower()
        datos = cargar_datos()
        personaje_encontrado = None


        for uid, info in datos.items():
            if uid == "_historial":
                continue

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


        if not inv_ids:
            lista_objetos = "*El inventario está vacío.*"
        else:

            lista_objetos = "\n".join([f"• {item_id}" for item_id in inv_ids])

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
            await ctx.send(f"No encontre ningun objeto con el ID: {item_id}")
            return


        embed = discord.Embed(
            title=item['nombre'],
            description=item.get("descripcion", "Sin descripcion."),
            color=discord.Color.blue()
        )


        embed.add_field(name="Precio", value=formatear_monedas(item['precio']), inline=True)


        cat = item.get("categoria", "General")
        cat_txt = ", ".join(cat) if isinstance(cat, list) else cat
        embed.add_field(name="Categoria", value=cat_txt, inline=True)


        stock_val = item.get("stock", "Infinito")
        embed.add_field(name="Stock", value=str(stock_val), inline=True)

        es_consumible = "Si" if item.get("consumible") else "No"
        embed.add_field(name="Consumible", value=es_consumible, inline=True)

        embed.set_footer(text=f"ID: {item['id']}")

        await ctx.send(embed=embed)

    # ---------- COMPRAR y Usar ----------
    @bot.command()
    async def comprar(ctx, alias: str, item_id: str):

        alias = alias.lower()
        item_id = item_id.lower()

        items = cargar_items()
        item = next((i for i in items if i["id"] == item_id), None)

        if not item:
            await ctx.send("Ese objeto no existe.")
            return

        datos = cargar_datos()
        uid = str(ctx.author.id)
        pj = datos.get(uid, {}).get("personajes", {}).get(alias)

        if not pj:
            await ctx.send("No tienes ese personaje.")
            return

        precio = item["precio"]
        oro_actual = pj.get("oro", 0)

        if oro_actual < precio:
            await ctx.send("No tienes suficiente oro.")
            return


        if item.get("stock") is not None:
            if item["stock"] <= 0:
                await ctx.send("Este objeto está agotado.")
                return
            item["stock"] -= 1
            guardar_items(items)


        pj["oro"] = oro_actual - precio

        if "inventario" not in pj:
            pj["inventario"] = []

        pj["inventario"].append(item["id"])

        guardar_datos(datos)

        await ctx.send(
            f"Compra realizada.\n"
            f"{pj['nombre']} compró {item['nombre']}.\n"
            f"Oro restante: {formatear_monedas(pj['oro'])}"
        )

    @bot.command()
    async def usar(ctx, alias: str, item_id: str):
        alias = alias.lower()
        item_id = item_id.lower()

        datos = cargar_datos()
        items = cargar_items()
        uid = str(ctx.author.id)
        pj = datos.get(uid, {}).get("personajes", {}).get(alias)

        if not pj:
            await ctx.send("No tienes ese personaje.")
            return

        inventario = pj.get("inventario", [])


        item_en_inv = next((x for x in inventario if x == item_id or x.startswith(f"{item_id} (")), None)

        if not item_en_inv:
            await ctx.send("No tienes ese objeto en tu inventario.")
            return


        item_base = next((i for i in items if i["id"] == item_id), None)
        if not item_base:
            await ctx.send("Ese objeto no existe en la base de datos de la tienda.")
            return


        if item_id == "kit_sanador_consumible":
            usos_actuales = 10  # Por defecto

            if "(" in item_en_inv:
                try:
                    usos_actuales = int(item_en_inv.split("(")[1].split(")")[0])
                except:
                    usos_actuales = 10

            nuevo_uso = usos_actuales - 1


            inventario.remove(item_en_inv)

            if nuevo_uso <= 0:
                await ctx.send(f"**{pj['nombre']}** usó la última carga del **{item_base['nombre']}**. ¡Se ha agotado!")
            else:

                nuevo_nombre_id = f"{item_id} ({nuevo_uso})"
                inventario.append(nuevo_nombre_id)
                await ctx.send(f"**{pj['nombre']}** usa el **{item_base['nombre']}**. Quedan **{nuevo_uso}** usos.")

            guardar_datos(datos)
            return


        await ctx.send(f"{pj['nombre']} usa **{item_base['nombre']}**.")

        if item_base.get("consumible", False):
            inventario.remove(item_en_inv)
            await ctx.send(f"El objeto **{item_base['nombre']}** se ha consumido.")

        guardar_datos(datos)
