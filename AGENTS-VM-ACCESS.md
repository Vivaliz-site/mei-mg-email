# Acesso dos agentes às VMs — revisão de acesso 2026-11-11

**Leitura obrigatória e fonte de verdade:** `Vivaliz-site/site-shopvivaliz` no `main`, especialmente `docs/knowledge/current-topology-and-access-2026-10-29.md`, `docs/knowledge/host-access.md` e `docs/knowledge/agent-rules.md`. Antes de operar, confirmar SHA, destino, identidade, autorização, lease e host real. **Não usar os aliases históricos `vm1`, `shopvivaliz-a1-site-raw` nem IP da origem.**

## Estrutura atual

| Conta OCI | Host | Função | Rota demonstrada |
|---|---|---|---|
| ESPOSA | `marina-a1-4c24g` | Produção web/DB/workers/runner | ShopVivaliz Remote Control MCP nativo, identidade e permissão efetiva verificadas em 11/11/2026; checar lease/ownership por comando |
| PRINCIPAL | `always-free-arm-1787907847-26` | Backend, MCP central, navegador corporativo, MEI/M365 e relays | ShopVivaliz Remote Control MCP (allowlist válida) e recuperação formal autorizada |
| PRINCIPAL, origem excluída | `shopvivaliz-free-a1` | **Nenhuma função operacional** | Não acessar, monitorar, usar Run Command, reativar nem recriar |

Os IPs privados e Tailscale atuais/observados estão no inventário canônico, não em aliases deste repositório. O status `TERMINATED` OCI ainda precisa de consulta direta ao lifecycle se necessário, mas a exclusão foi confirmada pelo proprietário. **Nunca** enviar comandos ao antigo `10.0.1.112` e não aproveitar a chave `shopvivaliz-free-a1-monitor` para Marina.

## Transporte, privilégio e MCPs

1. **Backend/MEI:** MCP central atualizado e testado em 11/11/2026; catálogo expõe backend, Marina e hosts Windows autorizados, sem origem descomissionada. O relay do KOCEPSV não respondeu nessa verificação, portanto sua execução não foi certificada.
2. **Marina:** MCP nativo central validado com `hostname -s; id -un` (exit 0, usuário ubuntu). O inventário não é grant de escrita; verificar operação autorizada, lease/fencing e privilégios por ferramenta. Preservar NoNewPrivileges/RBAC e não recorrer a outro transporte para contornar recusa de segurança.
3. **MCP próprio Marina:** rota independente com identidade/grant próprios; sua disponibilidade pública e autenticação precisam ser comprovadas na sessão específica, separadamente da rota central. Relatos de staging datados de 29/10 são históricos.
4. **OCI/SSH:** perfis, credenciais e tenancy separados, com host keys verificadas. Instance Agent/Run Command e serial console são meios oficiais de recuperação, **não** shells alternativos para burlar uma negativa de privilégio. Os comandos de 2026-09-06 para `sv-oci-vm-run vm1/vm2` são históricos e **não são instruções atuais**.
5. **Browser/GUI:** perfis corporativos isolados e navegador do agente no backend; Fred-Win é suporte de autenticação/OCI, não servidor web nem fallback automático do browser.

## Atenção especial ao túnel MEI

**Estado real comprovado em 2026-10-29:** no backend, `mei-mg-email-site-tunnel.service` estava `active (running)`, com `50-marina.conf` root-owned sobrescrevendo o comando SSH antigo por `ubuntu@100.118.170.46` e chave dedicada `mei-marina-forward`, `known_hosts_marina_verified` (ambos modo 0600). Na Marina, `127.0.0.1:18010/health` respondeu HTTP 200. **Este túnel SSH é independente do MCP OpenAI da Marina.**

O `main` atual usa uma unidade `mei-mg-email-site-tunnel.service` dedicada à rota SSH privada Marina, com chave local `mei-marina-forward`, host key verificada e `127.0.0.1:18010` restrito a loopback. A unidade pode possuir override operacional root-owned; **não** instalar o template antigo da VM excluída nem substituir os arquivos da instalação ativa por uma versão histórica. Antes de reiniciar, comparar `systemctl cat`, `systemctl show -p ExecStart`, SHA do repositório e rota real; confirmar HTTP 200 na Marina e persistência após reload/restart controlado. 

O runner `mei-ci-a1` localizado na Marina permaneceu desabilitado e sem `.runner`; o runner principal `mei-backend-a1` está online mas não deve substituir o CI secundário, porque este também faz backups. O registro GitHub do runner precisa ser concluído pelo mecanismo oficial autorizado, sem exibir tokens no chat/processos ou contornar bloqueios de segurança. `sender_blocked.pause` foi observado no backend e deve permanecer respeitado.

## Segurança e evidência

- Não revelar nem versionar chaves, tokens, OTPs, cookies, senhas ou dados protegidos.
- Validar `hostname`, `whoami`, versão SHA/serviço e owner da operação antes de comandos.
- Para qualquer falha, investigar causa raiz, corrigir se autorizado, prevenir, testar, revalidar runtime/UI/E2E; não encerrar por status/HTTP 200 isolado.
- Preservar rollback, exclusão mútua de writers, custos, aprovações e recusas explícitas.

**Histórico supersedido:** a versão de 2026-09-06 identificava `vm1` com `shopvivaliz-free-a1`, IP público anterior, aliases `shopvivaliz-a1-site-raw` e `vm2` como backend. Esse mapeamento foi invalidado pelo cutover de outubro; não copiar tais comandos para uso atual.
