# ~/.config/fish/functions/fish_greeting.fish
# Se você já tem um fish_greeting, só copie o bloco "pawdit" para dentro dele.
function fish_greeting
    # --- seu greeting atual (fastfetch, etc.) vai aqui ---

    # pawdit: só em login SSH interativo, uma vez por sessão (tmux/shell aninhado herdam a variável)
    if set -q SSH_TTY; and not set -q PAWDIT_SHOWN; and command -q pawdit
        set -gx PAWDIT_SHOWN 1
        pawdit greet
    end
end
