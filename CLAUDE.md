<!-- SHOPVIVALIZ_PR_CONDICIONAL_PTBR_20261108 -->
## Governança das PRs ShopVivaliz — regra transversal (08/11/2026)
- **Idioma:** toda PR criada por agentes deve ter título, descrição, justificativas, pedidos de revisão e comentários operacionais em **português brasileiro (pt-BR)**; manter nomes técnicos, caminhos, código e comandos no idioma original.
- **Aprovação dupla somente quando o diff INTRODUZIR, RESTAURAR ou AGRAVAR bloqueio, trava, restrição, permissão obrigatória, gate ou configuração que possa impedir a execução de comandos, operações, automações, deploys ou merge.** Nesses casos, exigir consentimento expresso do proprietário e revisões GitHub `APPROVED` das duas contas `shopvivaliz-human` e `fredmourao-ai`, no commit HEAD exato. PR protegida deve ser criada por terceira identidade autorizada (nenhuma das duas pode aprovar a própria PR).
- **PR comum:** documentação, correção técnica, teste, refatoração e melhoria que NÃO adicione nem agrave bloqueio não requerem dupla revisão por esta política; seguem o fluxo automático de correção, validação e integração. Outras revisões de segurança/comerciais já exigidas permanecem válidas.
- **Sem contorno:** nenhum agente/bot pode simular ou dispensar revisões, introduzir a restrição por outra rota, dividir mudança para escapar da regra, realizar push direto ou usar privilégios administrativos para desativar as proteções. Proteções obrigatórias do provedor, MFA e RBAC permanecem válidas.
- **Escopo:** todos os repositórios e agentes da organização Vivaliz-site, inclusive Claude, GPT, Codex, Gemini, ações automatizadas e MCPs. A classificação considera o efeito real da alteração; editar `AGENTS.md` ou workflow sem acrescentar restrição não aciona aprovação dupla.
<!-- /SHOPVIVALIZ_PR_CONDICIONAL_PTBR_20261108 -->

<!-- MANDATORY_AGENT_CHECKLIST_V1 -->
## Checklist proporcional: sem bloqueio global para tarefas rotineiras

**Revisao por determinacao do proprietario (06/11/2026):** foi revogada a obrigatoriedade universal de planejar e certificar um checklist a cada etapa, introduzida em 31/10/2026. A ausencia de `plan-checklist` nao pode impedir `record_progress`, retomada, correcao, teste ou conclusao de tarefas P0/P1 que ja possuam autorizacao. Um checkpoint duravel e uma proxima acao concreta continuam suficientes para registrar o trabalho; nao criar processo de aprovacao por subcomando.

`scripts/agent_task_state.py` deixa de injetar automaticamente um checklist exigivel em novos checkpoints do runtime canonico. Checkpoints anteriores com lista **vazia** nao ficam presos por um plano nunca iniciado. Para trabalhos que precisam de checklist formal, o executor pode ativar `SHOPVIVALIZ_REQUIRE_AGENT_CHECKLIST=1` no escopo do fluxo e usar `plan-checklist`, `next-step`, `check-step` e `add-checklist-step`. Se ja existem etapas planejadas, suas evidencias e integridade continuam obrigatorias para encerrar; nao apagar nem certificar etapas sem comprovacao.

Essa desburocratizacao nao autoriza falso sucesso nem remove controles independentes: identidade, MFA, RBAC, segredos, lease/fencing, aprovacoes humanas formalmente necessarias, branch protection, gates de operacoes comerciais, CI e validacao funcional/E2E pertinente. Nenhum controle novo deve ser imposto sem aprovacao do proprietario.
<!-- /MANDATORY_AGENT_CHECKLIST_V1 -->

<!-- EXTREME_AUDIT_UI_FIRST_HARD_GATE_V1 -->
> **AUDITORIA EXTREMA V5 = UI REAL OBRIGATORIA.** Antes de declarar `APTO` ou `CONCLUIDO`, o proprio agente percorre cada jornada material na interface grafica real (navegacao, cliques, preenchimento, resultado visivel, reload/revisita, persistencia e evidencia visual com ambiente/release). API, terminal, SQL, codigo, screenshot isolado, mocks e testes apenas headless nao substituem prova pela UI. A auditoria inclui investigacao, correcao e reauditoria visual apos reparo. Nao ocultar uma UI marcando `browser.required=false` ou `journey.ui=false`. Somente componentes comprovadamente sem UI podem usar excecao com inventario negativo documentado e evidencias. Em bloqueio de sessao, esgotar rotas autorizadas; nao burlar MFA/permissaos. Leia e obedeça a secao `EXTREME_AUDIT_UI_FIRST_HARD_GATE_V1` de `AGENTS.md` antes da tarefa.
<!-- /EXTREME_AUDIT_UI_FIRST_HARD_GATE_V1 -->

<!-- RESUME_EXECUTION_GATE_V1 -->
## Retome / Continue / Prossiga / Siga: execucao obrigatoria ate verificacao

Toda ordem Retome, Continue, Prossiga ou Siga e uma tarefa operacional de execucao, nao pedido de plano, status ou confirmacao generica. O agente principal, Claude, Gemini, Copilot e qualquer subagente devem ler as regras atuais do AGENTS.md no main e registrar prova nao secreta rules_loaded (fonte, ref, SHA, data) antes de mutacoes. Recuperar task_id, ultimo checkpoint e next_action com origem real; nao criar identidades de conversa ou sessoes ficticias.
Executar a proxima acao permitida; investigar erro, corrigir a causa, testar, fazer merge/deploy quando autorizado e validar o objetivo original no runtime. Persistir RUNNING com next_action real enquanto houver caminho seguro viavel; erro de ferramenta, timeout, status Pensando, PR ou ACK nao autorizam encerrar. CONCLUIDO exige evidencia fresca ponta a ponta; BLOCKED_EXTERNAL exige impedimento externo objetivo, alternativas seguras esgotadas e condicao exata de retomada. Quando disponivel, comprovar terminalidade com agent_task_state.py terminal --task <task_id>.
Nao contornar MFA, RBAC, aprovacao sensivel, branch protection ou direitos de outra sessao. Evitar mensagens intermediarias desnecessarias quando o proprietario pedir para nao postar; se limite externo interromper a execucao, salvar checkpoint verdadeiro e nao prometer trabalho de fundo sem mecanismo realmente ativo. Encaminhar as mesmas obrigacoes ao agente delegado.
<!-- /RESUME_EXECUTION_GATE_V1 -->

<!-- AUDIT_EXTERNAL_REMEDIATION_V1 -->
> **AUDITORIA EXTERNA:** também é corretiva. Se houver autorização de escrita, corrigir + testar + reauditar. Se o auditor for somente leitura/independente, o relatório não é estado terminal: encaminhar os achados a executor autorizado e manter a tarefa aberta até correção e revalidação independente ou bloqueio externo comprovado.
<!-- /AUDIT_EXTERNAL_REMEDIATION_V1 -->

<!-- AUDIT_REMEDIATE_VALIDATE_GLOBAL_V1 -->
> **AUDITORIA CORRETIVA OBRIGATÓRIA:** qualquer auditoria deve investigar causa raiz, corrigir achados materiais seguros/autorizados, prevenir recorrência quando pertinente, testar e reauditar. Não encerrar em relatório de erros. APTO/CONCLUIDO exige evidência fresca pós-correção/E2E aplicável. Fonte: `REGRAS-AGENTES-CENTRALIZADAS.md`.
<!-- /AUDIT_REMEDIATE_VALIDATE_GLOBAL_V1 -->

<!-- DIAGNOSTIC_REMEDIATE_VALIDATE_GLOBAL_V1 -->
> **DIAGNÓSTICO CORRETIVO GLOBAL:** diagnóstico confirmado obriga correção segura, prevenção pertinente, testes e validação real/E2E aplicável antes de `CONCLUIDO`; enquanto houver ação executável, permanecer `RUNNING`.
<!-- /DIAGNOSTIC_REMEDIATE_VALIDATE_GLOBAL_V1 -->
<!-- GEPETO_EVERY_TASK_V1 -->
## Gepeto obrigatorio em toda tarefa
Acione o plugin Gepeto junto com Superpowers em toda tarefa e retomada, sem nova mencao do usuario. Leia e cumpra `GEPETO-POLICY.md`. Se o runtime nao expuser o plugin, registre `GEPETO_UNAVAILABLE`, informe a limitacao e continue o trabalho autorizado sem simular participacao. Aplicar um plugin nao comprova delegacao nem revisao independente.
<!-- /GEPETO_EVERY_TASK_V1 -->

<!-- CLAUDE_READ_AGENTS_FIRST_V1 -->
> **BOOTSTRAP OBRIGATORIO DO CLAUDE:** antes de analisar, planejar, editar, executar comandos, usar navegador, abrir PR, fazer merge, deploy ou validar qualquer tarefa, leia **integralmente** o `AGENTS.md` da raiz deste repositorio e cumpra todas as instrucoes vigentes nele. Releia o `AGENTS.md` em retomadas de conversa ou quando o arquivo mudar. Se houver divergencia entre este `CLAUDE.md` e o `AGENTS.md`, o `AGENTS.md` prevalece. Nao prossiga assumindo memoria de uma leitura antiga.

@AGENTS.md

# Instrucoes para Claude

<!-- GLOBAL_BROWSER_VM_POLICY_V2 -->
> **NAVEGAÇÃO GLOBAL — VM OBRIGATÓRIA; WINDOWS PROIBIDO PARA BROWSER:** qualquer navegador, automação browser, sessão gráfica, Playwright/Selenium/CDP, Chrome/Chromium/Edge/Opera, CAPTCHA, MFA, consentimento ou validação visual deve usar por padrão e obrigatoriamente a VM backend `always-free-arm-1787907847-26` (`10.0.1.38`) e o Browser Worker privado. Para intervenção humana, usar `https://shopvivaliz.com.br/admin/browser-worker.php`. **Fred-Win (`LAPTOP-NIG4IFUU`) e `DESKTOP-KOCEPSV` não são destinos nem fallback para navegação.** Não perguntar qual máquina usar para browser: use a VM. Exceção somente se o proprietário ordenar explicitamente, na tarefa atual, o uso de um Windows específico para aquela navegação. Se a VM estiver indisponível, reparar o caminho VM/OCI Bastion/túnel privado ou registrar bloqueio real; nunca migrar silenciosamente para Windows. Workflows/relays Windows de browser são legado e não devem ser executados até serem migrados. A regra não proíbe Windows para tarefas não-browser que realmente dependam dele.


<!-- audit-refs: AUDIT_POLICY.md docs/quality/EXTREME_AUDIT_PROTOCOL.md docs/quality/AUDIT_RUNTIME_PARITY_V1.md docs/quality/AUDIT_UNIVERSAL_COVERAGE_V1.md docs/quality/ARCHITECTURE_DEPLOY_AUDIT_V1.md docs/quality/AUDIT_SELF_TEST_V1.md -->


<!-- SUPERPOWERS_EVERY_STAGE_V1 -->
> **@Superpowers CONTÍNUO E OBRIGATÓRIO:** toda conversa, sessão, agente e retomada de tarefa destes projetos deve usar @Superpowers **em cada etapa material**, não apenas no início. Reaplique a disciplina adequada ao passar por bootstrap/contexto, planejamento, investigação, coleta de evidências, implementação, debugging, TDD/testes, revisão, correção, PR/checks/merge, deploy, pós-deploy, auditoria e encerramento. Em `retome/continue/prossiga`, continue do último checkpoint comprovado sob @Superpowers. Se o runtime não expuser @Superpowers, registre `SUPERPOWERS_UNAVAILABLE` e aplique a metodologia equivalente sem fingir a chamada. Subagentes e automações delegadas herdam esta obrigação. Fonte local: `REGRAS-AGENTES-CENTRALIZADAS.md`; fonte canônica global: `Vivaliz-site/site-shopvivaliz`.

Antes de qualquer trabalho neste repositorio, leia e cumpra `AGENTS.md` e `AI-TO-CLI-PROTOCOL.md`. A regra `Isolamento obrigatorio de sessao CLI por chat` e vinculante: este chat nao pode reutilizar sessao CLI pertencente a outro chat.
Regra de continuidade: leia e cumpra `AI-TO-CLI-PROTOCOL.md`, especialmente `Continuidade obrigatoria diante de falha de ferramenta ou comando`; erro de ferramenta nao autoriza encerrar a tarefa.

Antes de finalizar qualquer tarefa, cumpra o `PROTOCOLO OBRIGATORIO DE CONCLUSAO DE TAREFAS` de `AI-TO-CLI-PROTOCOL.md`; nao pare em erro corrigivel ou resultado parcial.

<!-- EXECUTION_PROVENANCE_POLICY_V1 -->
@EXECUTION-PROVENANCE-POLICY.md


<!-- BROWSER_SESSION_POLICY_V1 -->
Leia e cumpra AGENTS.md e a secao BROWSER_SESSION_POLICY_V1 de REGRAS-AGENTES-CENTRALIZADAS.md antes de qualquer uso de navegador.


<!-- AUDIT_ABSOLUTE_V5_ENTRYPOINT -->
Leia primeiro `AGENTS.md`. Para auditoria/aptidão, cumpra `AUDIT_ABSOLUTE_GATE_V1.md`, `AUDIT_BROWSER_E2E_REAL_V1.md`, `AUDIT_AUTH_CREDENTIAL_DISCOVERY_V1.md`, `AUDIT_PROJECT_REQUIREMENTS_V1.md` e o manifesto local de requisitos. Somente o certifier pode autorizar APTO.


<!-- AUDIT_MERGE_ENFORCEMENT_V1 -->
<!-- audit-refs: AGENTS.md docs/quality/AUDIT_ABSOLUTE_GATE_V1.md docs/quality/AUDIT_BROWSER_E2E_REAL_V1.md docs/quality/AUDIT_AUTH_CREDENTIAL_DISCOVERY_V1.md docs/quality/AUDIT_MERGE_ENFORCEMENT_V1.md docs/quality/AUDIT_PROJECT_REQUIREMENTS_V1.md -->

<!-- GLOBAL_TASK_CONTINUITY_V8 -->
## Global task continuity V8
Toda tarefa que possa alterar código, infraestrutura, dados, CI ou deploy deve manter checkpoint durável via `python3 scripts/agent_task_state.py`. Este repositório é fixado como `repository=Vivaliz-site/mei-mg-email`. Falhas recuperáveis permanecem RUNNING e conclusão exige verificação fresca. O adapter falha fechado sem o controlador canônico injetado pelo runtime detached. Background recovery permanece Gemini-only; Codex nunca é fallback automático e continua sendo a última opção finita explícita.
<!-- /GLOBAL_TASK_CONTINUITY_V8 -->
