# 0002 · En streaming, reintentar y cambiar de proveedor solo antes del primer fragmento

- **Estado:** aceptada
- **Fecha:** 2026-11-12

## Contexto

En `complete` es seguro reintentar o pasar a otro proveedor: la respuesta llega completa o no
llega. En `stream` el texto se entrega a medida que se genera. Hasta la versión 1.0, `stream`
cambiaba de proveedor al primer fallo sin reintentar, de modo que una caída breve del modelo
local enviaba la petición a la nube aunque un segundo intento habría funcionado.

## Decisión

- La apertura del stream y la espera del **primer fragmento** se hacen dentro del mismo bucle de
  reintentos que usa `complete` (backoff exponencial y `Retry-After`).
- Si todos los intentos fallan antes del primer fragmento, se pasa al siguiente proveedor.
- Una vez entregado el primer fragmento, cualquier fallo se propaga a quien llama.
- `stream` acepta `model` con la misma regla que `complete`: se aplica solo al primer proveedor.

## Consecuencias

- Nunca se mezclan dos respuestas de modelos distintos en una misma salida.
- Quien consume el stream debe manejar un error a mitad de respuesta (por ejemplo, descartar el
  texto parcial y reintentar la operación completa).
