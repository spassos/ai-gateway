"""Obtém o Google ID token via gcloud — sem fluxo OAuth próprio (Princípio 5)."""

import shutil
import subprocess


class GcloudError(RuntimeError):
    pass


def get_identity_token() -> str:
    if not shutil.which("gcloud"):
        raise GcloudError(
            "gcloud não encontrado. Instale o Google Cloud SDK "
            "(https://cloud.google.com/sdk/docs/install) e rode `gcloud auth login`."
        )
    result = subprocess.run(
        ["gcloud", "auth", "print-identity-token"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise GcloudError(
            "Falha ao obter o identity token. Autentique-se primeiro com a conta "
            f"corporativa: `gcloud auth login`.\n{result.stderr.strip()}"
        )
    return result.stdout.strip()
