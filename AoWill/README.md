# BOT DE LICHSEA.

EL Bot de Lichsea permite el manejo de fichas, nivel, exp, oro, lootboxes, tienda y más.

##  Personajes
* `!addpj [exp] [link] [nombre]` : Registra un nuevo personaje.
* `!call [alias]` : Muestra la ficha completa, edad, ubicación y cajas.
* `!setnacimiento [alias] [dia] [mes] [año]` : Define el cumpleaños de tu personaje.
* `!viajar [alias] [destino]` : Inicia un viaje (14 días de cooldown).

## Economía e Inventario
* `!oro [alias]` : Muestra cuánto dinero tiene el personaje.
* `!inventario [alias]` : Lista los objetos y el oro del personaje.
* `!tienda [categoria]` : Abre el catálogo de objetos.
* `!ver [item_id]` : Muestra la descripción detallada de un objeto.
* `!comprar [alias] [item_id]` : Adquiere un objeto de la tienda.
* `!vender [alias] [item_id]` : Vende un objeto a la tienda por 1/5 de su valor.
* `!usar [alias] [item_id]` : Usa un objeto (consume cargas si aplica).

## Intercambios y Desarrollo
* `!trade [item_id] [mi_pj] [target_pj] [precio_po]` : Propone un intercambio a otro jugador.
* `!trade_accept [vendedor_alias] [mi_pj_alias]` : Acepta un intercambio activo.
* `!entrenar [alias] [opcion]` : Elige un beneficio diario (alimentación, concentrado, especializado, los 3 grandes).

##  Cajas de Botín
* `!tiendalootbox` : Muestra las cajas, precios, drops y el banner activo.
* `!comprarbox [alias] [rareza]` : Compra una caja usando el oro del PJ (Límite: 2 diarias).
* `!abrirbox [alias] [rareza]` : Abre una caja de tu inventario para obtener tu recompensa.

## Administración (Staff)
*Estos comandos solo son accesibles para el Staff.*
* `!addexp / !removeexp [alias] [cantidad]` : Gestiona la experiencia.
* `!daroro / !quitaroro [alias] [cantidad]` : Gestiona el dinero (en PC).
* `!dar_espacio [usuario] [cantidad]` : Cambia el límite de PJs vivos.
* `!setestado [alias] [Estado]` : Cambia a Vivo, Muerto o Retirado.
* `!reportexp` : Procesa recompensas grupales (usar en threads).
* `!forcedelpj [alias]` : Elimina un personaje del sistema.
* `!dar_objeto [alias] [item_id]` : Entrega un objeto o dote directa al inventario.
* `!darbox [alias/all_characters] [rareza] [cantidad]` : Regala cajas a un PJ o a todos los vivos.
* `!revisardrops [pool]` : Audita los objetos cargados en cada rareza

## Cómo usar
1. Instala los requerimientos: `pip install discord.py`
2. Configura las constantes en `main.py`.
3. Ejecuta con `python main.py`.