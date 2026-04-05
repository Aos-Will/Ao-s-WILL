
import discord
import os
import json
from discord.ext import tasks, commands
from datetime import datetime, timedelta

import tienda #módulo de tienda
import personajes  # módulo de personajes


TOKEN = 'MTQ2OTUyNjczNzA5MTE3MDMyNA.G0ioeu.W9pnc3LVHiVS3t_tFsv8tPpOtVy8ed-0H-3pEY'
ID_CANAL_VOZ = 1469531271037194374
ARCHIVO_DATOS = 'datos_lichsea.json'

# INTENTS
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


personajes.setup(bot)
tienda.setup(bot)


# --------------------------------------------------

def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        with open(ARCHIVO_DATOS, 'r', encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "dia": 3,
            "mes": 2,
            "año": 1,
            "ultima_actualizacion": datetime.now().isoformat()
        }


def guardar_datos(datos):
    with open(ARCHIVO_DATOS, 'w', encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)


datos_mundo = cargar_datos()


async def verificar_cumpleaños():
    canal = bot.get_channel(1359009580859789312)
    if not canal:
        return

    datos = cargar_datos()
    dia_actual = datos_mundo["dia"]
    mes_actual = datos_mundo["mes"]

    for uid, info in datos.items():
        if uid in ["dia", "mes", "año", "ultima_actualizacion"]:
            continue

        if isinstance(info, dict) and "personajes" in info:
            for pj in info["personajes"].values():
                if pj.get("estado", "Vivo") == "Vivo":
                    nac = pj.get("nacimiento")
                    if nac and nac.get("dia") == dia_actual and nac.get("mes") == mes_actual:
                        await canal.send(f"🎂 ¡Feliz cumpleaños, **{pj['nombre']}**!")


@bot.event
async def on_ready():
    print(f'Bot Lichsea conectado como {bot.user}')
    await calcular_tiempo_transcurrido()
    if not actualizar_reloj_lichsea.is_running():
        actualizar_reloj_lichsea.start()


async def calcular_tiempo_transcurrido():
    global datos_mundo
    ahora = datetime.now()
    ultima_vez = datetime.fromisoformat(datos_mundo["ultima_actualizacion"])

    diferencia = ahora - ultima_vez
    periodos_pasados = int(diferencia.total_seconds() // (12 * 3600))

    if periodos_pasados > 0:
        for _ in range(periodos_pasados):
            sumar_un_dia()
            await verificar_cumpleaños()

        datos_mundo["ultima_actualizacion"] = (
                ultima_vez + timedelta(hours=12 * periodos_pasados)
        ).isoformat()

        guardar_datos(datos_mundo)
        await actualizar_nombre_canal()
    else:
        await verificar_cumpleaños()


def sumar_un_dia():
    global datos_mundo
    datos_mundo["dia"] += 1
    if datos_mundo["dia"] >= 30:
        datos_mundo["dia"] = 0
        datos_mundo["mes"] += 1
    if datos_mundo["mes"] >= 12:
        datos_mundo["mes"] = 0
        datos_mundo["año"] += 1


async def actualizar_nombre_canal():
    nuevo_nombre = f"📅 Lichsea: D{datos_mundo['dia']} M{datos_mundo['mes']} A{datos_mundo['año']}"
    channel = bot.get_channel(ID_CANAL_VOZ)
    if channel:
        try:
            await channel.edit(name=nuevo_nombre)
        except:
            pass


@tasks.loop(hours=12)
async def actualizar_reloj_lichsea():
    sumar_un_dia()
    datos_mundo["ultima_actualizacion"] = datetime.now().isoformat()
    guardar_datos(datos_mundo)
    await actualizar_nombre_canal()
    await verificar_cumpleaños()


bot.run(TOKEN)