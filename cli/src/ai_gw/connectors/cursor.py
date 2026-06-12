"""Connector do Cursor: não há arquivo de config programático — instruções guiadas.

LIMITAÇÃO DO CURSOR: apenas chat/composer aceitam endpoint customizado.
Tab/autocomplete e parte do Agent continuam no backend da Cursor e NÃO passam
pelo gateway (não são auditados nem contam no budget).
"""

from ..store import Credentials


def instructions(credentials: Credentials) -> str:
    base_url = f"{credentials.base_url.rstrip('/')}/v1"
    return f"""
Configuração manual do Cursor (não há arquivo de config programático):

  1. Abra Cursor Settings → Models
  2. Em "OpenAI API Key", ative "Override OpenAI Base URL" e preencha:
       Base URL: {base_url}
       API Key:  {credentials.api_key}
  3. Clique em "Verify" e adicione os modelos do gateway pelo nome exato
     (veja `ai-gw models`), ex.: claude-sonnet-4-6, gemini-2.5-pro

ATENÇÃO — limitação do Cursor: somente o chat/composer usa o endpoint
customizado. Tab/autocomplete e partes do Agent continuam nos servidores da
Cursor: esse tráfego NÃO passa pelo gateway (sem auditoria, fora do budget).
"""
