{ config, lib, pkgs, ... }:
# Uso (configuration.nix):
#   imports = [ ./pawdit/contrib/nixos/pawdit.nix ];
#   services.pawdit.enable = true;
let
  cfg = config.services.pawdit;
  tomlFormat = pkgs.formats.toml { };

  pawdit = pkgs.python3Packages.buildPythonApplication {
    pname = "pawdit";
    version = "0.2.0";
    pyproject = true;
    src = lib.cleanSource ../..;
    build-system = [ pkgs.python3Packages.setuptools ];
    doCheck = false;
    meta.mainProgram = "pawdit";
  };
in
{
  options.services.pawdit = {
    enable = lib.mkEnableOption "auditoria semanal de segurança com resumo por LLM pequeno";

    schedule = lib.mkOption {
      type = lib.types.str;
      default = "Sun *-*-* 03:30";
      description = "OnCalendar do systemd.";
    };

    model = lib.mkOption {
      type = lib.types.str;
      default = "qwen3:1.7b";
      description = "Modelo do Ollama (use um <2B para rodar bem em CPU).";
    };

    manageOllama = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Liga services.ollama (CPU) e baixa o modelo (precisa de nixpkgs com services.ollama.loadModels).";
    };

    group = lib.mkOption {
      type = lib.types.str;
      default = "wheel";
      description = "Grupo que pode ler os relatórios.";
    };

    extraPackages = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      example = lib.literalExpression "[ pkgs.aide ]";
      description = "Ferramentas extras para os coletores (aide, trivy...). Cada uma só é usada se estiver no PATH.";
    };

    settings = lib.mkOption {
      type = tomlFormat.type;
      default = { };
      example = lib.literalExpression ''{ expected_ports = [ 22 25565 ]; max_ai_findings = 8; }'';
      description = "Conteúdo extra do /etc/pawdit.toml.";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ pawdit ];

    environment.etc."pawdit.toml".source =
      tomlFormat.generate "pawdit.toml" ({ model = cfg.model; state_group = cfg.group; } // cfg.settings);

    services.ollama = lib.mkIf cfg.manageOllama {
      enable = true;
      loadModels = [ cfg.model ];
    };

    systemd.tmpfiles.rules = [ "d /var/lib/pawdit 2770 root ${cfg.group} -" ];

    systemd.services.pawdit = {
      description = "pawdit — auditoria semanal de segurança";
      after = [ "network-online.target" ] ++ lib.optional cfg.manageOllama "ollama.service";
      wants = [ "network-online.target" ];
      path = [
        pawdit
        pkgs.lynis pkgs.vulnix pkgs.ssh-audit pkgs.chkrootkit pkgs.audit
        pkgs.iproute2 pkgs.systemd pkgs.openssh
        pkgs.coreutils pkgs.gnugrep pkgs.gnused pkgs.gawk pkgs.findutils pkgs.procps pkgs.util-linux pkgs.nettools pkgs.kmod
      ] ++ cfg.extraPackages;
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${pawdit}/bin/pawdit run";
        Environment = "PAWDIT_CONFIG=/etc/pawdit.toml";
        Nice = 10;
        IOSchedulingClass = "idle";
        TimeoutStartSec = "3h";
      };
    };

    systemd.timers.pawdit = {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = cfg.schedule;
        Persistent = true; # roda ao ligar se o horário foi perdido
        RandomizedDelaySec = "30min";
      };
    };
  };
}
