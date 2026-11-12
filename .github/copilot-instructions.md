<!-- MANDATORY_AGENT_CHECKLIST_V1 -->
## Checklist proporcional — sem exigencia universal

Por autorizacao expressa do proprietario (06/11/2026), nenhuma tarefa P0/P1 previamente autorizada fica bloqueada por falta de checklist transacional formal, `plan-checklist` ou certificacao de cada subcomando. Registrar evidencias reais e `next_action` no checkpoint. O checklist pode ser ativado quando necessario, e seus itens ja planejados continuam exigindo provas verdadeiras para encerrar.

Preservar continuidade ate concluir com verificacao, testes e CI pertinentes. Nao diminuir MFA, RBAC, sigilo, protecao de branch, revisao humana de grants, leases/fencing, protecoes comerciais e recusas de provedores. E proibido reintroduzir burocracia geral sem consentimento do proprietario.
<!-- /MANDATORY_AGENT_CHECKLIST_V1 -->

<!-- RESUME_EXECUTION_GATE_V1 -->
## Retome / Continue / Prossiga / Siga: execucao obrigatoria ate verificacao

Toda ordem Retome, Continue, Prossiga ou Siga e uma tarefa operacional de execucao, nao pedido de plano, status ou confirmacao generica. O agente principal, Claude, Gemini, Copilot e qualquer subagente devem ler as regras atuais do AGENTS.md no main e registrar prova nao secreta rules_loaded (fonte, ref, SHA, data) antes de mutacoes. Recuperar task_id, ultimo checkpoint e next_action com origem real; nao criar identidades de conversa ou sessoes ficticias.
Executar a proxima acao permitida; investigar erro, corrigir a causa, testar, fazer merge/deploy quando autorizado e validar o objetivo original no runtime. Persistir RUNNING com next_action real enquanto houver caminho seguro viavel; erro de ferramenta, timeout, status Pensando, PR ou ACK nao autorizam encerrar. CONCLUIDO exige evidencia fresca ponta a ponta; BLOCKED_EXTERNAL exige impedimento externo objetivo, alternativas seguras esgotadas e condicao exata de retomada. Quando disponivel, comprovar terminalidade com agent_task_state.py terminal --task <task_id>.
Nao contornar MFA, RBAC, aprovacao sensivel, branch protection ou direitos de outra sessao. Evitar mensagens intermediarias desnecessarias quando o proprietario pedir para nao postar; se limite externo interromper a execucao, salvar checkpoint verdadeiro e nao prometer trabalho de fundo sem mecanismo realmente ativo. Encaminhar as mesmas obrigacoes ao agente delegado.
<!-- /RESUME_EXECUTION_GATE_V1 -->

# GitHub Copilot / coding agents

Antes de qualquer trabalho, leia e cumpra `AGENTS.md` e `AI-TO-CLI-PROTOCOL.md`. A secao `Continuidade obrigatoria diante de falha de ferramenta ou comando` e vinculante: uma falha de CLI/API/tool nao encerra a tarefa; diagnostique, use fallback seguro, persista checkpoint e continue ate CONCLUIDO ou bloqueio externo real.

<!-- MARINA_MCP_AS_USER_20261112 -->
> **MCP Marina: executar como `ubuntu` e root do backend (2026-11-12):** `marina_admin_shell` aceita o argumento opcional `as_user="ubuntu"` (sudo -n -u ubuntu, auditado por hash; exclusivo com `as_root`; qualquer outro usuario e recusado). Ativo na Marina desde a release `eb81e37c` (grant PR #3918 do `site-shopvivaliz`). No backend, o usuario `root` tambem tem os MCPs `shopvivaliz-marina-admin` e `shopvivaliz-remote-control` e a credencial do Marina MCP ja provisionada. Fonte de verdade e procedimento: `Vivaliz-site/site-shopvivaliz` em `docs/knowledge/marina-mcp-admin-agent-access.md`. Credenciais continuam so em arquivos protegidos (0600), sem expor valores.
