"""CLI `ai-gw` — conecta seus clientes de código ao AI Gateway corporativo.

Fluxo: `ai-gw login` → `ai-gw connect claude-code` → pronto.
"""

import os
from enum import StrEnum

import typer
from rich.console import Console
from rich.table import Table

from . import broker_client, gcloud_auth, store
from .connectors import claude_code, codex, cursor
from .store import Credentials

app = typer.Typer(help="AI Gateway: acesso corporativo aos modelos do Vertex AI.")
console = Console()

DEFAULT_BROKER_URL = os.environ.get("AI_GW_BROKER_URL", "http://localhost:8080")


class Client(StrEnum):
    claude_code = "claude-code"
    codex = "codex"
    cursor = "cursor"


def _require_credentials() -> Credentials:
    credentials = store.load()
    if credentials is None:
        console.print("[red]Você não está logado.[/red] Rode [bold]ai-gw login[/bold] primeiro.")
        raise typer.Exit(code=1)
    return credentials


@app.command()
def login(
    broker_url: str = typer.Option(DEFAULT_BROKER_URL, help="URL do broker do gateway."),
    dev_email: str = typer.Option(None, help="SOMENTE DEV LOCAL: pula o gcloud e usa este e-mail."),
) -> None:
    """Autentica via gcloud e provisiona sua key pessoal (rotaciona a anterior)."""
    try:
        if dev_email:
            result = broker_client.provision(broker_url, dev_email=dev_email)
        else:
            console.print("Obtendo identity token via [bold]gcloud[/bold]...")
            id_token = gcloud_auth.get_identity_token()
            result = broker_client.provision(broker_url, id_token=id_token)
    except (gcloud_auth.GcloudError, broker_client.BrokerError) as exc:
        console.print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    credentials = Credentials(
        api_key=result["api_key"],
        base_url=result["base_url"],
        user_email=result["user_email"],
        broker_url=broker_url,
    )
    path = store.save(credentials)
    budget = result.get("budget", {})
    console.print(f"[green]Logado como {credentials.user_email}[/green]")
    console.print(f"Credenciais salvas em {path} (0600)")
    console.print(
        f"Budget: US$ {budget.get('spent', 0):.2f} / {budget.get('max', 0):.2f} no período"
    )
    console.print("Agora rode [bold]ai-gw connect claude-code[/bold] (ou codex / cursor).")


@app.command()
def connect(client: Client = typer.Argument(..., help="Cliente a conectar.")) -> None:
    """Configura um cliente (Claude Code, Codex ou Cursor) para usar o gateway."""
    credentials = _require_credentials()

    if client is Client.claude_code:
        path = claude_code.connect(credentials)
        console.print(f"[green]Claude Code conectado.[/green] Config: {path}")
        console.print("Abra um novo terminal e rode [bold]claude[/bold] normalmente.")
    elif client is Client.codex:
        config_path, env_file = codex.connect(credentials)
        console.print(f"[green]Codex conectado.[/green] Config: {config_path}")
        console.print(
            f"A key fica em variável de ambiente. Adicione ao seu shell rc:\n"
            f"  [bold]source {env_file}[/bold]"
        )
    elif client is Client.cursor:
        console.print(cursor.instructions(credentials))


@app.command()
def models() -> None:
    """Lista os modelos disponíveis no gateway (GET /v1/models)."""
    credentials = _require_credentials()
    try:
        data = broker_client.list_models(credentials.base_url, credentials.api_key)
    except broker_client.BrokerError as exc:
        console.print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Modelos disponíveis")
    table.add_column("Modelo")
    table.add_column("Owner")
    for model in data:
        table.add_row(model.get("id", "?"), model.get("owned_by", "-"))
    console.print(table)


@app.command()
def status() -> None:
    """Mostra seu gasto atual, limite e data de reset."""
    credentials = _require_credentials()
    try:
        result = broker_client.me(credentials.broker_url, credentials.api_key)
    except broker_client.BrokerError as exc:
        console.print(f"[red]Erro:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    budget = result.get("budget", {})
    spent = budget.get("spent") or 0.0
    max_budget = budget.get("max") or 0.0
    console.print(f"Usuário:  {result.get('user_email')}")
    console.print(f"Gasto:    US$ {spent:.2f} / {max_budget:.2f}")
    if budget.get("period_end"):
        console.print(f"Reset em: {budget['period_end']}")
    if max_budget and spent >= max_budget:
        console.print("[red]Budget esgotado — requisições bloqueadas até o reset.[/red]")


@app.command()
def logout() -> None:
    """Remove as credenciais locais e desfaz as configs dos clientes."""
    removed_claude = claude_code.disconnect()
    removed_codex = codex.disconnect()
    removed_credentials = store.clear()
    if removed_credentials or removed_claude or removed_codex:
        console.print("[green]Logout concluído.[/green] Configs locais removidas.")
        console.print("A key antiga será revogada automaticamente no próximo login (rotação).")
    else:
        console.print("Nada a remover — você não estava logado.")


if __name__ == "__main__":
    app()
