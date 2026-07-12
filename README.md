# 🎟 Gestor de Rifas

Aplicación de escritorio en **Python** para llenar y administrar los datos de una rifa,
con **tema claro y oscuro**. Todo se guarda en un archivo **CSV** que puedes abrir
también en Excel o Google Sheets.

## Funciones

- **Crear una rifa nueva**: pones el nombre de la rifa, el rango de boletos que te
  tocaron (por ejemplo del 1 al 100) y los campos que quieras capturar por boleto
  (Nombre, Teléfono, Correo, Método de pago… los que tú decidas). La columna
  **Boleto** se genera automáticamente.
- **Ciclo de captura**: lo inicias y lo detienes cuando quieras. Te va presentando
  boleto por boleto (solo los vacíos) para llenar sus datos; guardas con **Enter**
  y pasa al siguiente. También puedes omitir boletos.
- **Vista CSV**: ves la tabla completa dentro de la aplicación; las filas ya
  llenadas se marcan en verde. Doble clic en una fila para editar ese boleto.
- **Resumen**: cuántos boletos llevas vendidos/llenados, cuántos siguen vacíos,
  el porcentaje de avance, y las listas de **qué números ya se vendieron** y
  **cuáles faltan** (compactadas, ej. `1-3, 5, 7-20`).
- **Agregar más números**: amplía la rifa con más boletos cuando lo necesites;
  los números repetidos se omiten solos.
- **Abrir rifa existente**: retoma cualquier CSV creado por la app para seguir
  llenándolo otro día.
- **Importar un CSV que ya tenías**: si abres un CSV con otro formato (por
  ejemplo hecho en Excel), un asistente te pregunta cuál columna contiene el
  número de boleto. Si el archivo no tiene números de boleto, la app **añade
  la columna por ti**: tú eliges el rango de números (ej. del 100 al 150) y
  en qué posición insertar la columna; si el rango es más grande que las
  filas, los números sobrantes quedan como boletos vacíos por vender. El
  archivo adaptado se guarda donde tú elijas.

## Requisitos

- Python 3.8 o superior con Tkinter (viene incluido en la instalación estándar
  de Python en Windows y macOS; en Linux instala `python3-tk` si hace falta:
  `sudo apt install python3-tk`).
- No necesita ninguna librería externa.

## Cómo descargarlo y ejecutarlo

1. Descarga el archivo [`rifa.py`](rifa.py) (o clona este repositorio).
2. Ejecuta:

   ```bash
   python rifa.py
   ```

   En algunos sistemas el comando es `python3 rifa.py`. En Windows también
   puedes hacer doble clic sobre `rifa.py`.

## Formato del CSV

Debe existir una columna `Boleto` (en cualquier posición; las rifas creadas
por la app la ponen al inicio) y el resto son los campos que definiste:

```csv
Boleto,Nombre,Teléfono,Método de pago
1,Ana López,5551112233,Efectivo
2,Juan Pérez,5554445566,Transferencia
3,,,
```

Un boleto cuenta como **vendido/llenado** cuando tiene al menos un campo con datos.
