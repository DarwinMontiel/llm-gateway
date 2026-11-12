"""CLI ``puente``: preguntar a un modelo local o en la nube y comparar proveedores."""

from __future__ import annotations

import logging
from typing import Any

import typer
from typer.core import TyperCommand, TyperGroup

from puente_llm.config import PROVIDERS, Settings, build_gateway, build_provider
from puente_llm.errors import AllProvidersFailedError, ProviderError
from puente_llm.providers import OllamaProvider
from puente_llm.types import Message

AYUDA = "Muestra esta ayuda y termina."

_TEXTOS_DE_AYUDA = {
    "ARGUMENTS_PANEL_TITLE": "Argumentos",
    "OPTIONS_PANEL_TITLE": "Opciones",
    "COMMANDS_PANEL_TITLE": "Comandos",
    "DEFAULT_STRING": "[por defecto: {}]",
    "REQUIRED_LONG_STRING": "[obligatorio]",
    "ABORTED_TEXT": "Cancelado.",
    "RICH_HELP": "Usa [blue]'{command_path} {help_option}'[/] para ver la ayuda.",
}


def _traducir_ayuda() -> None:
    """Traduce los títulos de los paneles de ayuda de Typer (formato con rich).

    Si una versión futura de Typer los renombra, la ayuda sigue funcionando con los títulos
    originales: solo se reemplazan los que existen.
    """
    try:
        from typer import rich_utils
    except ImportError:  # pragma: no cover - Typer instalado sin rich
        return
    for name, text in _TEXTOS_DE_AYUDA.items():
        if hasattr(rich_utils, name):
            setattr(rich_utils, name, text)


_traducir_ayuda()


class _GrupoEnEspanol(TyperGroup):
    def get_help_option(self, ctx: Any) -> Any:
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = AYUDA
        return option


class _ComandoEnEspanol(TyperCommand):
    def get_help_option(self, ctx: Any) -> Any:
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = AYUDA
        return option


app = typer.Typer(
    help="Un puente entre tu modelo local (Ollama) y la nube (Groq): si uno no responde, "
    "el otro toma el relevo.",
    cls=_GrupoEnEspanol,
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def principal(
    detalle: bool = typer.Option(
        False, "--detalle", "-v", help="Muestra los reintentos y cambios de proveedor."
    ),
) -> None:
    """Un puente entre tu modelo local (Ollama) y la nube (Groq)."""
    if detalle:
        logging.basicConfig(level=logging.WARNING, format="  · %(message)s")
    else:
        logging.basicConfig(level=logging.ERROR)


def pregunta(
    prompt: str = typer.Argument(..., help="Pregunta o instrucción."),
    proveedor: str = typer.Option(
        "auto", "--proveedor", "-p", help="ollama | groq | auto (local primero, nube de respaldo)."
    ),
    sistema: str | None = typer.Option(None, "--sistema", "-s", help="Instrucción de sistema."),
    modelo: str | None = typer.Option(
        None, "--modelo", "-m", help="Modelo del primer proveedor (el respaldo usa el suyo)."
    ),
    stream: bool = typer.Option(
        True, "--stream/--sin-stream", help="Mostrar la respuesta a medida que se genera."
    ),
) -> None:
    """Envía un prompt y muestra la respuesta."""
    order = list(PROVIDERS) if proveedor == "auto" else [proveedor]
    try:
        with build_gateway(order) as gateway:
            if stream:
                for chunk in gateway.stream(prompt, system=sistema, model=modelo):
                    typer.echo(chunk, nl=False)
                typer.echo()
            else:
                completion = gateway.complete(prompt, system=sistema, model=modelo)
                typer.echo(completion.text)
                typer.secho(
                    f"\n[{completion.provider} · {completion.model} · "
                    f"{completion.latency_ms:.0f} ms]",
                    fg=typer.colors.BRIGHT_BLACK,
                )
    except AllProvidersFailedError as error:
        typer.secho(str(error), fg=typer.colors.RED, err=True)
        typer.secho(
            "Sugerencia: inicia Ollama (ollama serve) o define GROQ_API_KEY para usar la nube.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(1) from error
    except (ProviderError, ValueError) as error:
        typer.secho(str(error), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error


def compara(
    prompt: str = typer.Argument(..., help="Prompt que se envía a ambos proveedores."),
) -> None:
    """Ejecuta el mismo prompt en Ollama y Groq y compara latencia y tokens."""
    settings = Settings()
    typer.echo(f"{'proveedor':<10} {'modelo':<26} {'latencia':>10} {'tokens':>8} {'tok/s':>7}")
    for name in PROVIDERS:
        provider = build_provider(name, settings)
        try:
            result = provider.complete([Message.user(prompt)])
        except ProviderError as error:
            typer.secho(f"{name:<10} {'—':<26} {error!s}", fg=typer.colors.YELLOW)
            continue
        finally:
            close = getattr(provider, "close", None)
            if callable(close):
                close()
        typer.echo(
            f"{result.provider:<10} {result.model:<26} {result.latency_ms:>8.0f}ms "
            f"{result.completion_tokens or 0:>8} {result.tokens_per_second or 0:>7}"
        )


def modelos() -> None:
    """Lista los modelos descargados en Ollama."""
    settings = Settings()
    try:
        with OllamaProvider(settings.ollama_url, timeout=settings.timeout_seconds) as ollama:
            nombres = ollama.list_models()
    except ProviderError as error:
        typer.secho(str(error), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error
    if not nombres:
        typer.echo("Ollama no tiene modelos descargados (prueba: ollama pull llama3.2).")
    for name in nombres:
        typer.echo(name)


# Nombres en español; los anteriores en inglés quedan como alias ocultos por compatibilidad.
for _funcion, _nombre, _alias in (
    (pregunta, "pregunta", "ask"),
    (compara, "compara", "compare"),
    (modelos, "modelos", "models"),
):
    app.command(_nombre, cls=_ComandoEnEspanol)(_funcion)
    app.command(_alias, cls=_ComandoEnEspanol, hidden=True)(_funcion)


if __name__ == "__main__":
    app()
