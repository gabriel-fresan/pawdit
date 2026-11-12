# pawdit >:3

**P**aranoid **A**dmin's **W**eekly **D**igest of **I**ssues & **T**hreats

Auditoria semanal de segurança para Linux: orquestra as ferramentas que você já conhece (Lynis, ssh-audit, AIDE, chkrootkit, vulnix, Trivy, auditd, Docker/Podman), compara com a semana anterior e usa um **LLM pequeno local (<2B, só CPU, via Ollama) para escrever o resumo e as sugestões de correção**. A versão curta aparece quando você entra por SSH (veja o exemplo no [README](README.md)).

## Como funciona

1. Um timer do systemd (semanal, `Persistent=true`) roda `pawdit run` como root.
2. Coletores rodam para cada ferramenta encontrada no `PATH` e normalizam a saída em achados (id estável, severidade, detalhe, sugestão da ferramenta). Checagens próprias cobrem units falhas, portas abertas, UID 0 / senha vazia e `sshd -T`.
3. Os achados são comparados com a última rodada: **novo / persistente / resolvido**.
4. O LLM só *escreve texto* a partir dessa lista: um resumo de 1 frase, uma dica curta por achado do topo e um texto "por que importa / como corrigir / cuidado" por achado. Os fatos do greeting (score, contagens) vêm do código, não do modelo. Nenhuma tool ou função é exposta a ele.
5. Se o Ollama estiver fora do ar, o relatório sai igual, com resumo por regras.

## Instalação

**Ubuntu / Debian**
```bash
sudo apt update && sudo apt install -y lynis aide chkrootkit auditd ssh-audit python3-venv
sudo aideinit -y -f && sudo cp /var/lib/aide/aide.db.new /var/lib/aide/aide.db
curl -fsSL https://ollama.com/install.sh | sh && ollama pull qwen3:1.7b
git clone https://github.com/gabriel-fresan/pawdit && cd pawdit && sudo ./install.sh
pawdit doctor && sudo pawdit run
```
O Trivy não está no apt do Ubuntu: instale pelo guia oficial, com versão fixada e checksum conferido.

**NixOS**: importe `contrib/nixos/pawdit.nix` e use `services.pawdit.enable = true;`.
**Fedora / Bazzite**: `sudo ./install.sh`. Como root, o Lynis precisa pertencer a root: use o pacote da distro ou `git clone` em `/usr/local/lynis` seguido de `chown -R 0:0`. Via Homebrew ele falha.
**Greeting no SSH**: copie `contrib/shell/pawdit.fish` (ou `.bash`).

Reinstalar é seguro (idempotente); `--uninstall` preserva config e histórico.

## Uso

`pawdit` (greeting) · `report` · `list` · `fix [N|ID]` (sem argumento abre um menu compacto) · `diff` · `history` · `raw <ferramenta>` · `doctor` · `sudo run` · `sudo ai --model X` (regera só os textos).

## Status e limites

Testado com um report real do Lynis 3.1.8, checagens próprias, lógica de diff e a camada de IA contra um Ollama falso (45 testes). Os parsers de AIDE, vulnix, Trivy, ssh-audit e Docker foram testados com amostras escritas à mão: fixtures reais são bem-vindas. O módulo NixOS só teve a sintaxe validada. Mais detalhes em [SECURITY.md](SECURITY.md) e [CONTRIBUTING.md](CONTRIBUTING.md).

Licença MIT.
