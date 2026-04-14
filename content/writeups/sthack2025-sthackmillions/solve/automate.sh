#!/usr/bin/env bash
# usage: ./automate.sh HH:MM:SS [YYYY-MM-DD]
# Predicts the lottery draw for a given time using the known reference seed.

REF_DATE="2025-05-23"
REF_TIME="01:11:54"
REF_SEED=2360

STEP_SEC=$((5*60))
SEED_STEP=10
MODULO=3000

[[ $# -lt 1 ]] && { echo "Usage: $0 HH:MM:SS [YYYY-MM-DD]"; exit 1; }

TIME_STR="$1"
DATE_STR="${2:-$REF_DATE}"

t_target=$(date -d "$DATE_STR $TIME_STR" +%s)
t_ref=$(date   -d "$REF_DATE $REF_TIME"  +%s)
diff=$((t_target - t_ref))

steps=$((diff / STEP_SEC))
(( diff < 0 && diff % STEP_SEC )) && (( steps-- ))

seed=$(( (REF_SEED + steps * SEED_STEP) % MODULO ))
(( seed < 0 )) && seed=$(( seed + MODULO ))

echo "$seed" > index.txt
draw=$(faketime "$DATE_STR $TIME_STR" ./lotogiciel 2>/dev/null)

printf "Heure  : %s %s\nSeed   : %d\nTirage : %s\n" \
       "$DATE_STR" "$TIME_STR" "$seed" "$draw"
