# ~/.bashrc (ou /etc/profile.d/pawdit.sh) — bash/zsh
if [[ $- == *i* && -n ${SSH_TTY:-} && -z ${PAWDIT_SHOWN:-} ]] && command -v pawdit >/dev/null 2>&1; then
  export PAWDIT_SHOWN=1
  pawdit greet
fi
