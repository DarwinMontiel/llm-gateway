"""CLI ``llm``: preguntar a un modelo local o en la nube y comparar proveedores."""

from __future__ import annotations

import typer

from llm_gateway.config import Settings, build_gateway, build_provider
from llm_gateway.errors import AllProvidersFailedError, ProviderError
from llm_gateway.types import Message

app = typer.Typer(help="Cliente unificado para Ollama (local) y Groq (nube).", no_args_is_help=True)


@app.command()
def ask(
    prompt: str = typer.Argument(..., help="Pregunta o instrucción."),
    provider: str = typer.Option(
        "auto", help="ollama | groq | auto (local primero, nube de respaldo)."
    ),
    system: str | None = typer.Option(None, help="Instrucción de sistema."),
    stream: bool = typer.Option(True, help="Mostrar la respuesta a medida que se genera."),
) -> None:
    """Envía un prompt y muestra la respuesta."""
    order = ["ollama", "groq"] if provider == "auto" else [provider]
    try:
        gateway = build_gateway(order)
        if stream:
            for chunk in gateway.stream(prompt, system=system):
                typer.echo(chunk, nl=False)
            typer.echo()
        else:
            completion = gateway.complete(prompt, system=system)
            typer.echo(completion.text)
            typer.secho(
                f"\n[{completion.provider} · {completion.model} · {completion.latency_ms:.0f} ms]",
                fg=typer.colors.BRIGHT_BLACK,
            )
    except (AllProvidersFailedError, ProviderError, ValueError) as error:
        typer.secho(str(error), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error


@app.command()
def compare(prompt: str = typer.Argument(...)) -> None:
    """Ejecuta el mismo prompt en Ollama y Groq y compara latencia y tokens."""
    settings = Settings()
    typer.echo(f"{'proveedor':<10} {'modelo':<26} {'latencia':>10} {'tokens':>8} {'tok/s':>7}")
    for name in ("ollama", "groq"):
        try:
            result = build_provider(name, settings).complete([Message.user(prompt)])
        except ProviderError as error:
            typer.secho(f"{name:<10} {'—':<26} {error!s}", fg=typer.colors.YELLOW)
            continue
        typer.echo(
            f"{result.provider:<10} {result.model:<26} {result.latency_ms:>8.0f}ms "
            f"{result.completion_tokens or 0:>8} {result.tokens_per_second or 0:>7}"
        )


@app.command()
def models() -> None:
    """Lista los modelos descargados en Ollama."""
    from llm_gateway.providers import OllamaProvider

    settings = Settings()
    try:
        for name in OllamaProvider(settings.ollama_url).list_models():
            typer.echo(name)
    except ProviderError as error:
        typer.secho(str(error), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from error


if __name__ == "__main__":
    app()
