import json
import os
import re
import asyncio
import discord
from discord.ext import commands, tasks
from datetime import datetime

ARCHIVO_DATOS = "personajes.json"
MAX_EXP = 355000

# ====== PERMISOS ======
ADMIN_ID = 995843251200327753
DRAGON_ROLE_ID = 1410886251556638860
COSTO_VIAJE_COBRE = 500
REGIONES_VALIDAS = ["Heloserra", "Kaerdan", "Arkanvale", "Tharion", "Sylervian"]
ROL_VIAJE_ID = 1469538752220234004

    # ====== ASEGURADORA DE VIRUS ======
LINK_REGEX = re.compile(
    r"^https:\/\/nivel20\.com\/games\/dnd-5\/characters\/\d+(?:-[a-zA-Z0-9_-]+)?$"
)

ALIAS_REGEX = re.compile(r"\[\s*([A-Za-z0-9]+)\s*\]")
EXP_REGEX = re.compile(r"(\d+)\s*EXP", re.IGNORECASE)
ORO_REGEX = re.compile(r"(\d+)\s*(PO|PC)", re.IGNORECASE)

# ====== TABLA NIVELES ======
TABLA_NIVELES = [
    (0, 1), (300, 2), (900, 3), (2700, 4),
    (6500, 5), (14000, 6), (23000, 7),
    (34000, 8), (48000, 9), (64000, 10),
    (85000, 11), (100000, 12), (120000, 13),
    (140000, 14), (165000, 15), (195000, 16),
    (225000, 17), (265000, 18), (305000, 19),
    (355000, 20)
]

# ================= AUUUUU :3 DRAGONCOSAS =================

def calcular_nivel(exp: int) -> int:
    nivel = 1
    for xp, lvl in TABLA_NIVELES:
        if exp >= xp:
            nivel = lvl
    return nivel

def cargar_datos():
    if not os.path.exists(ARCHIVO_DATOS):
        return {}
    try:
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def guardar_datos(datos):
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


def obtener_fecha_mundo():
    try:
        with open("datos_lichea.json", "r", encoding="utf-8") as f:
            datos = json.load(f)
            return {

                "dia": datos.get("dia", 1),

                "mes": datos.get("mes", 1),

                "año": datos.get("año", 1)

            }
    except:
        return {"dia": 1, "mes": 1, "año": 1}


def calcular_edad(nacimiento, actual, estado):
    if estado == "Muerto":
        return "Fallecido"

    if not nacimiento:
        return "Desconocida"
    edad = actual["año"] - nacimiento["año"]
    if (actual["mes"], actual["dia"]) < (nacimiento["mes"], nacimiento["dia"]):
        edad -= 1

    return max(0, edad)

def registrar_cambio(datos, uid, alias, exp_anterior):
    datos.setdefault("_historial", [])
    datos["_historial"].append({
        "uid": uid,
        "alias": alias,
        "exp_anterior": exp_anterior,
        "timestamp": datetime.utcnow().isoformat()
    })

def tiene_permiso_exp(ctx):
    if ctx.author.id == ADMIN_ID:
        return True
    return any(rol.id == DRAGON_ROLE_ID for rol in ctx.author.roles)

# ================= SETUP =================

def setup(bot: commands.Bot):

    # ---------- ADD PJ ----------
    @bot.command()
    async def addpj(ctx, exp: int, link: str, *, nombre: str):
        nombre = nombre.strip()

        if not nombre or len(nombre) > 50:
            await ctx.send("Nombre inválido.")
            return

        if exp < 0:
            await ctx.send("La EXP no puede ser negativa.")
            return

        exp = min(exp, MAX_EXP)

        if not LINK_REGEX.match(link):
            await ctx.send("Link inválido de nivel20.")
            return

        alias = nombre.split()[0].lower()
        if not alias.isalnum():
            await ctx.send("Alias inválido.")
            return

        datos = cargar_datos()
        uid = str(ctx.author.id)

        datos.setdefault(uid, {"personajes": {}})
        personajes = datos[uid]["personajes"]

        # Cambio solicitado: solo cuentan los que están "Vivo"
        personajes_vivos = [
            pj for pj in personajes.values()
            if pj.get("estado", "Vivo") == "Vivo"
        ]

        if len(personajes_vivos) >= 4:
            await ctx.send("Máximo de personajes alcanzado.")
            return

        if alias in personajes:
            await ctx.send("Ese personaje ya existe.")
            return

        personajes[alias] = {
            "nombre": nombre,
            "exp": exp,
            "nivel": calcular_nivel(exp),
            "link": link,
            "estado": "Vivo",
            "oro": 0
        }

        guardar_datos(datos)

        await ctx.send(
            f"Personaje creado:\n"
            f"**{nombre}**\n"
            f"Nivel {personajes[alias]['nivel']} | EXP {exp}"
        )

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

    @bot.command()
    async def daroro(ctx, alias: str, cantidad: int):

        if not any(rol.id == ADMIN_ID for rol in ctx.author.roles):
            await ctx.send("No tienes permiso.")
            return

        if cantidad <= 0:
            await ctx.send("Cantidad inválida.")
            return

        alias = alias.lower()
        datos = cargar_datos()

        for uid, info in datos.items():
            if uid == "_historial":
                continue

            pj = info.get("personajes", {}).get(alias)
            if pj:
                oro_actual = pj.get("oro", 0)
                pj["oro"] = oro_actual + cantidad
                guardar_datos(datos)

                await ctx.send(
                    f"Cobre añadido a **{pj['nombre']}**\n"
                    f"Oro: {oro_actual} → {pj['oro']} PC"
                )
                return

        await ctx.send("Personaje no encontrado.")

    @bot.command()
    async def setnacimiento(ctx, alias: str, dia: int, mes: int, año: int):
        datos = cargar_datos()
        uid = str(ctx.author.id)
        pj = datos.get(uid, {}).get("personajes", {}).get(alias.lower())

        if pj:
            pj["nacimiento"] = {"dia": dia, "mes": mes, "año": año}
            guardar_datos(datos)
            await ctx.send(f"Fecha de nacimiento de **{pj['nombre']}** guardada correctamente.")
        else:
            await ctx.send("No se encontro el personaje.")

    @bot.command()
    async def viajar(ctx, alias: str, *, destino: str):
        destino = destino.title()
        if destino not in REGIONES_VALIDAS:
            await ctx.send(f"Región no válida. Opciones: {', '.join(REGIONES_VALIDAS)}")
            return

        datos = cargar_datos()
        uid = str(ctx.author.id)
        alias = alias.lower()
        pj = datos.get(uid, {}).get("personajes", {}).get(alias)

        if not pj:
            await ctx.send("No tienes ese personaje.")
            return

        # No se puede viajar si está muerto charlotte
        if pj.get("estado") == "Muerto":
            await ctx.send(f"**{pj['nombre']}** está muerto. Los muertos no viajan.")
            return

        # Revisar cooldown
        if pj.get("llegada") is not None:
            await ctx.send(f"**{pj['nombre']}** ya está en medio de un viaje (Cooldown activo).")
            return

        if pj.get("oro", 0) < COSTO_VIAJE_COBRE:
            await ctx.send(f"No tienes oro suficiente (5 PO).")
            return

        cal = obtener_fecha_mundo()
        d, m, a = cal["dia"] + 14, cal["mes"], cal["año"]

        while d > 30:
            d -= 30
            m += 1
        while m > 12:
            m -= 12
            a += 1

        pj["oro"] -= COSTO_VIAJE_COBRE
        pj["ubicacion"] = f"Viajando a {destino}"
        pj["llegada"] = {"dia": d, "mes": m, "año": a, "destino": destino}
        guardar_datos(datos)

        rol = ctx.guild.get_role(ROL_VIAJE_ID)
        if rol: await ctx.author.add_roles(rol)

        await ctx.send(f"**{pj['nombre']}** ha partido hacia {destino}. Llegará el día {d}/{m}/{a}.")

        # Rol de Discord
        rol = ctx.guild.get_role(ROL_VIAJE_ID)
        if rol: await ctx.author.add_roles(rol)

        await ctx.send(f"**{pj['nombre']}** ha partido hacia {destino}. Llegará (fin de cooldown) el día {d}/{m}/{a}.")

    @bot.command()
    async def quitaroro(ctx, alias: str, cantidad: int):

        if not any(rol.id == ADMIN_ID for rol in ctx.author.roles):
            await ctx.send("No tienes permiso.")
            return

        if cantidad <= 0:
            await ctx.send("Cantidad inválida.")
            return

        alias = alias.lower()
        datos = cargar_datos()

        for uid, info in datos.items():
            if uid == "_historial":
                continue

            pj = info.get("personajes", {}).get(alias)
            if pj:
                oro_actual = pj.get("oro", 0)
                nuevo_oro = max(oro_actual - cantidad, 0)
                pj["oro"] = nuevo_oro
                guardar_datos(datos)

                await ctx.send(
                    f"Oro removido de **{pj['nombre']}**\n"
                    f"Oro: {formatear_monedas(oro_actual)} → {formatear_monedas(pj['oro'])}"
                )
                return

        await ctx.send("Personaje no encontrado.")

    @bot.command()
    async def setestado(ctx, alias: str, estado: str):
        if not any(rol.id == ADMIN_ID for rol in ctx.author.roles):
            await ctx.send("No tienes permiso.")
            return

        estado = estado.capitalize()

        if estado not in ["Vivo", "Muerto", "Retirado"]:
            await ctx.send("Estado inválido. Usa: Vivo, Muerto o Retirado.")
            return

        alias = alias.lower()
        datos = cargar_datos()

        for uid, info in datos.items():
            if uid == "_historial":
                continue

            pj = info.get("personajes", {}).get(alias)
            if pj:
                pj["estado"] = estado
                guardar_datos(datos)
                await ctx.send(
                    f"Estado actualizado:\n"
                    f"**{pj['nombre']}** ahora está {estado}"
                )
                return

        await ctx.send("Personaje no encontrado.")

    @bot.command()
    async def forcedelpj(ctx, alias: str):

        if not any(rol.id == ADMIN_ID for rol in ctx.author.roles):
            await ctx.send("No tienes permiso.")
            return

        alias = alias.lower()
        datos = cargar_datos()

        for uid, info in datos.items():
            if uid == "_historial":
                continue

            if alias in info.get("personajes", {}):
                nombre = info["personajes"][alias]["nombre"]
                del info["personajes"][alias]
                guardar_datos(datos)
                await ctx.send(f"Personaje eliminado: **{nombre}**")
                return

        await ctx.send("Personaje no encontrado.")

    @bot.command(name="AyudaBot", aliases=["info", "comandos", "ayudame"])
    async def ayudabot(ctx):
        embed = discord.Embed(
            title="Lista de Comandos",
            description="Usa el prefijo ! antes de cada comando. Este mensaje se borrara en 5 minutos.",
            color=discord.Color.blue()
        )

        # --- Gestion de Personaje ---
        embed.add_field(
            name="Personajes",
            value=(
                "**addpj [exp] [link] [nombre]**: Registra un nuevo personaje.\n"
                "**call [alias]**: Muestra la ficha completa, edad y ubicacion.\n"
                "**setnacimiento [alias] [dia] [mes] [año]**: Define el cumple de tu PJ.\n"
                "**viajar [alias] [destino]**: Inicia un viaje (14 dias de cooldown)."
            ),
            inline=False
        )

        # --- Economia e Inventario ---
        embed.add_field(
            name="Economia e Inventario",
            value=(
                "**oro [alias]**: Muestra cuanto dinero tiene el personaje.\n"
                "**inventario [alias]**: Lista los objetos y el oro del personaje.\n"
                "**tienda [categoria]**: Abre el catalogo de objetos.\n"
                "**ver [item_id]**: Muestra la descripcion detallada de un objeto.\n"
                "**comprar [alias] [item_id]**: Adquiere un objeto de la tienda.\n"
                "**usar [alias] [item_id]**: Usa un objeto (consume cargas si aplica)."
            ),
            inline=False
        )

        # --- Administracion (Solo Staff) ---
        embed.add_field(
            name="Administracion",
            value=(
                "**addexp / removeexp [alias] [cantidad]**: Gestiona la experiencia.\n"
                "**daroro / quitaroro [alias] [cantidad]**: Gestiona el dinero (en PC).\n"
                "**setestado [alias] [Estado]**: Cambia a Vivo, Muerto o Retirado.\n"
                "**reportexp**: (En threads) Procesa recompensas grupales.\n"
                "**forcedelpj [alias]**: Elimina un personaje del sistema."
            ),
            inline=False
        )

        embed.set_footer(text="ID de Staff: Admin o Rol Dragon")

        # borrado automatico en 300 segundos
        await ctx.send(embed=embed, delete_after=300)


        try:
            await ctx.message.delete()
        except:
            pass

    # ---------- ADD EXP ----------
    @bot.command()
    async def addexp(ctx, alias: str, cantidad: int):
        if not tiene_permiso_exp(ctx):
            await ctx.send("No tienes permiso.")
            return

        if cantidad <= 0:
            await ctx.send("Cantidad inválida.")
            return

        alias = alias.lower()
        datos = cargar_datos()

        for uid, info in datos.items():
            if uid == "_historial":
                continue

            pj = info.get("personajes", {}).get(alias)
            if pj:
                exp_anterior = pj["exp"]
                nueva_exp = min(exp_anterior + cantidad, MAX_EXP)

                registrar_cambio(datos, uid, alias, exp_anterior)

                pj["exp"] = nueva_exp
                pj["nivel"] = calcular_nivel(nueva_exp)
                guardar_datos(datos)

                await ctx.send(
                    f"EXP añadida a **{pj['nombre']}**\n"
                    f"EXP: {exp_anterior} → {pj['exp']}\n"
                    f"Nivel: {pj['nivel']}"
                )
                return

        await ctx.send("Ese personaje no existe.")

    @bot.command()
    async def reportexp(ctx):
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send("Este comando solo funciona dentro de un thread.")
            return

        if not tiene_permiso_exp(ctx):
            await ctx.send("No tienes permiso para reportar recompensas.")
            return

        mensaje_base = None
        async for msg in ctx.channel.history(limit=30, oldest_first=False):
            if msg.id == ctx.message.id:
                continue
            if ALIAS_REGEX.search(msg.content):
                mensaje_base = msg
                break

        if not mensaje_base:
            await ctx.send("No se encontró un mensaje válido con personajes en el thread.")
            return

        aliases_unicos = list(dict.fromkeys([a.strip().lower() for a in ALIAS_REGEX.findall(mensaje_base.content)]))

        # ====== EXTRACCIÓN ======
        exp_match = EXP_REGEX.search(mensaje_base.content)
        oro_match = ORO_REGEX.search(mensaje_base.content)

        cantidad_exp = int(exp_match.group(1)) if exp_match else 0
        cantidad_oro_cobre = 0
        if oro_match:
            valor = int(oro_match.group(1))
            tipo = oro_match.group(2).upper()
            cantidad_oro_cobre = valor * 100 if tipo == "PO" else valor

        if cantidad_exp <= 0 and cantidad_oro_cobre <= 0:
            await ctx.send("No se detectó ni EXP ni Oro válido.")
            return

        datos = cargar_datos()
        resultados = []

        # ====== PROCESAMIENTO ÚNICO ======
        for alias in aliases_unicos:
            aplicado = False
            for uid, info in datos.items():
                if uid == "_historial": continue
                pj = info.get("personajes", {}).get(alias)
                if pj:
                    cambios = []
                    if cantidad_exp > 0:
                        exp_ant = pj["exp"]
                        registrar_cambio(datos, uid, alias, exp_ant)
                        pj["exp"] = min(exp_ant + cantidad_exp, MAX_EXP)
                        pj["nivel"] = calcular_nivel(pj["exp"])
                        cambios.append(f"EXP: {exp_ant} -> {pj['exp']} (Nivel {pj['nivel']})")

                    if cantidad_oro_cobre > 0:
                        oro_ant = pj.get("oro", 0)
                        pj["oro"] = oro_ant + cantidad_oro_cobre
                        cambios.append(f"Oro: {formatear_monedas(oro_ant)} -> {formatear_monedas(pj['oro'])}")

                    resultados.append(f"**{pj['nombre']}**:\n" + "\n".join(f"  └ {c}" for c in cambios))
                    aplicado = True
                    break
            if not aplicado:
                resultados.append(f"**{alias}**: ❌ no encontrado")

        guardar_datos(datos)

        # ====== REPORTE FINAL ======
        recompensa_detectada = []
        if cantidad_exp > 0: recompensa_detectada.append(f"{cantidad_exp} EXP")
        if cantidad_oro_cobre > 0: recompensa_detectada.append(formatear_monedas(cantidad_oro_cobre))

        await ctx.send(
            f"🐉 **Procesado:** {', '.join(recompensa_detectada)}\n\n" +
            "\n".join(resultados)
        )


    # ---------- REMOVE EXP ----------
    @bot.command()
    async def removeexp(ctx, alias: str, cantidad: int):
        if not tiene_permiso_exp(ctx):
            await ctx.send("No tienes permiso.")
            return

        if cantidad <= 0:
            await ctx.send("Cantidad inválida.")
            return

        alias = alias.lower()
        datos = cargar_datos()

        for uid, info in datos.items():
            if uid == "_historial":
                continue

            pj = info.get("personajes", {}).get(alias)
            if pj:
                exp_anterior = pj["exp"]
                nueva_exp = max(exp_anterior - cantidad, 0)

                registrar_cambio(datos, uid, alias, exp_anterior)

                pj["exp"] = nueva_exp
                pj["nivel"] = calcular_nivel(nueva_exp)
                guardar_datos(datos)

                await ctx.send(
                    f"EXP removida de **{pj['nombre']}**\n"
                    f"EXP: {exp_anterior} → {pj['exp']}\n"
                    f"Nivel: {pj['nivel']}"
                )
                return

        await ctx.send("Ese personaje no existe.")

    # ---------- CALL ----------

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return

        if message.content.lower().startswith("!call"):
            alias = message.content[5:].strip().lower()
            if not alias:
                return

            datos = cargar_datos()
            cal = obtener_fecha_mundo()
            uid_autor = str(message.author.id)

            es_staff = (message.author.id == ADMIN_ID or
                        any(rol.id == DRAGON_ROLE_ID for rol in message.author.roles))

            info_usuario = datos.get(uid_autor, {})
            personajes_usuario = info_usuario.get("personajes", {})
            pj = personajes_usuario.get(alias)

            if not pj and es_staff:
                for uid_busqueda, info in datos.items():
                    if uid_busqueda == "_historial": continue
                    pj_encontrado = info.get("personajes", {}).get(alias)
                    if pj_encontrado:
                        pj = pj_encontrado
                        break

            if not pj:
                await message.channel.send("No tienes ese personaje registrado.")
                return

            llegada = pj.get("llegada")
            if llegada:
                if (cal["año"], cal["mes"], cal["dia"]) >= (llegada["año"], llegada["mes"], llegada["dia"]):
                    pj["ubicacion"] = llegada["destino"]
                    pj["llegada"] = None
                    guardar_datos(datos)

                    otros_viajando = any(p.get("llegada") is not None for p in personajes_usuario.values())
                    if not otros_viajando:
                        rol_v = message.guild.get_role(ROL_VIAJE_ID)
                        if rol_v and rol_v in message.author.roles:
                            try:
                                await message.author.remove_roles(rol_v)
                            except:
                                pass

            cd_compra = pj.get("cooldown_compra")
            txt_compra = "Puedes comprar"

            if cd_compra:

                if (cal["año"], cal["mes"], cal["dia"]) >= (cd_compra["año"], cd_compra["mes"], cd_compra["dia"]):
                    pj["cooldown_compra"] = None
                    guardar_datos(datos)
                    txt_compra = "✅ Disponible"
                else:
                    txt_compra = f"⏳ Bloqueado hasta el {cd_compra['dia']}/{cd_compra['mes']}/{cd_compra['año']}"

            estado_salud = pj.get("estado", "Vivo")
            nacimiento = pj.get("nacimiento")
            resultado_edad = calcular_edad(nacimiento, cal, estado_salud)

            txt_nacimiento = "Desconocido"
            if nacimiento:
                meses_nombres = [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ]
                idx_mes = max(0, min(abs(nacimiento["mes"]) - 1, 11))
                nombre_mes = meses_nombres[idx_mes]
                era = "ADC" if nacimiento["año"] < 0 else "DDC"
                txt_nacimiento = f"{nacimiento['dia']} de {nombre_mes} del año {abs(nacimiento['año'])} {era}"

            if resultado_edad in ["Fallecido", "Desconocida"]:
                txt_edad = resultado_edad
            else:
                txt_edad = f"{resultado_edad} años"
                if nacimiento and cal["dia"] == nacimiento["dia"] and cal["mes"] == nacimiento["mes"]:
                    txt_edad += " 🎂 ¡Hoy es su cumple!"

            ubicacion_actual = pj.get("ubicacion", "Desconocida")
            oro_txt = formatear_monedas(pj.get("oro", 0))

            await message.channel.send(
                f"**{pj['nombre']}**\n"
                f"Edad: {txt_edad}\n"
                f"Nacimiento: {txt_nacimiento}\n"
                f"Ubicación: {ubicacion_actual}\n"
                f"Estado de salud: {estado_salud}\n"
                f"Nivel: {pj['nivel']} | EXP: {pj['exp']}\n"
                f"Oro: {oro_txt}\n"
                f"Cooldown Compra: {txt_compra}\n"
                f"Link: {pj['link']}"
            )

        await bot.process_commands(message)

    @bot.command()
    async def oro(ctx, alias: str):

            alias = alias.lower()
            datos = cargar_datos()

            for uid, info in datos.items():
                if uid == "_historial":
                    continue

                pj = info.get("personajes", {}).get(alias)
                if pj:
                    oro_actual = pj.get("oro", 0)
                    await ctx.send(
                        f"**{pj['nombre']}** tiene {formatear_monedas(oro_actual)}"
                    )
                    return

            await ctx.send("Personaje no encontrado.")


