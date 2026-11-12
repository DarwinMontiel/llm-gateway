# 0003 · Un respaldo sin credenciales se omite

- **Estado:** aceptada
- **Fecha:** 2026-11-12

## Contexto

El modo por defecto es "local primero, nube de respaldo" (`["ollama", "groq"]`). Hasta la
versión 1.0, `GroqProvider` exigía la clave al construirse, así que quien solo tenía Ollama no
podía usar ese modo: el programa terminaba con `falta GROQ_API_KEY` antes de intentar el modelo
local.

## Decisión

- `GroqProvider` valida la clave **al usarse**, no al construirse, y expone `configured`.
- `build_gateway` omite, con un aviso en el log, los proveedores **de respaldo** sin
  credenciales.
- Si el proveedor sin credenciales es el primero o el único, se conserva: al usarlo se produce
  un `AuthenticationError` con un mensaje claro, que no se reintenta ni se oculta.

## Consecuencias

- Quien solo tiene Ollama usa el modo por defecto sin configurar nada más.
- Una configuración incompleta de la nube no pasa desapercibida: queda en el log (visible con
  `puente -v`) y, si la nube es el proveedor principal, se reporta como error.
