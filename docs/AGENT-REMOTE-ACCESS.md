# Acesso remoto dos agentes MEI-MG — rotas verificadas 2026-11-11

Este documento é obrigatório para tarefas de VM, email, API, runtime, deploy, logs, navegador ou recuperação. Fonte superior e atualizada: `Vivaliz-site/site-shopvivaliz/docs/knowledge/current-topology-and-access-2026-10-29.md` e `host-access.md` no `main`.

## Hosts e rotas efetivas

- `marina-a1-4c24g` (**OCI ESPOSA**) — produção web/deploy/MySQL/workers. Rota principal **ShopVivaliz Remote Control MCP**; chamada administrativa nativa de 11/11/2026 confirmou `marina-a1-4c24g`/`ubuntu`, exit 0. Verificar grant e lease antes de cada mutação.
- `always-free-arm-1787907847-26` (**OCI PRINCIPAL**) — backend/controlador MCP/MEI-MG/M365/browser corporativo. ShopVivaliz Remote Control é a rota central para hosts válidos da allowlist. Verificar `hosts_list`/`host_health` antes de executar.
- `shopvivaliz-free-a1` (**excluída**) — **NUNCA** usar `10.0.1.112`, alias SSH, túnel legado, chave associada, retries ou recuperação de runner; não recriar.
- Fred-Win e KOCEPSV são estações auxiliares e não hosts de produção.

## MCP e acesso privado

O MCP central atual anuncia backend, Marina, Fred-Win e KOCEPSV; a origem excluída não integra o catálogo. A rota administrativa da Marina foi testada via MCP nativo em 11/11/2026. O MCP independente da Marina requer verificação de identidade e grant próprios; um serviço Cloudflare ativo isoladamente não comprova autenticação. Para operações normais usar o MCP central; SSH privado/Tailscale é mecanismo separado de recuperação autorizada, não atalho após negativa de segurança.

O navegador de agentes e seus perfis Dev/Atendimento permanecem no backend, preservando sessões e MFA, sem cópia de cookies. Não copiar chaves privadas ou secretos entre tenants/hosts.

## Túnel site ↔ MEI-MG e prevenção de regressões

A rota efetiva já foi recuperada por um drop-in privado autorizado `/etc/systemd/system/mei-mg-email-site-tunnel.service.d/50-marina.conf`: serviço ativo no backend, SSH para Marina via Tailscale `100.118.170.46`, host key dedicada e encaminhamento local `127.0.0.1:18010`. A Marina confirmou HTTP **200** em `http://127.0.0.1:18010/health` (snapshot 2026-10-29). **Não confundir esse túnel com o MCP independente OpenAI, ainda não registrado.**

O `main` usa agora a rota privada da Marina no template do túnel, sob chave SSH dedicada e host key verificada. Antes de atualizar o runtime, inspecionar a unidade efetiva com `systemctl cat` e preservar eventuais drop-ins root-owned; confirmar destino autorizado, listener loopback e health E2E. Não desabilitar o serviço Marina que já opera, não imprimir chaves/tokens, não reativar `shopvivaliz-free-a1`. O runner dedicado `mei-ci-a1` está instalado mas sem registro local e offline, deixando os checks GitHub sem executor. Não usar o runner principal de e-mails para CI Docker ou backups.

Antes de qualquer mutação, ler os runbooks atuais, identificar host/usuário reais, validar SHA/estado ativo e registrar evidência; correção exige testes e confirmação E2E apropriada. Documentos de setembro são históricos.
