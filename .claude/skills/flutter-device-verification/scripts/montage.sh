#!/bin/bash
# 把多張截圖縮小拼成一張總覽圖，一次看完一組畫面（需要 ffmpeg）。
# 用法：montage.sh <輸出.png> <截圖...>
# 每列 COLS 張（預設 7），每張縮成 W×H（預設 270×585，約等於直式手機的比例）；
# 平板或橫式截圖改 W、H。總覽圖只用來找異常，像素層的細節（導覽列、按鍵的下緣厚度、
# 1px 線）要回原圖裁切放大看。
set -u
out="${1:?輸出路徑}"; shift
COLS="${COLS:-7}"; W="${W:-270}"; H="${H:-585}"
[ "$#" -ge 2 ] || { echo "montage.sh: 至少要兩張截圖（ffmpeg xstack 的下限）" >&2; exit 2; }
ins=(); f=""; lay=""; i=0
for p in "$@"; do
  ins+=(-i "$p")
  f="${f}[${i}:v]scale=${W}:${H}[v${i}];"
  x=$(( (i % COLS) * W )); y=$(( (i / COLS) * H ))
  lay="${lay}${x}_${y}|"
  i=$((i + 1))
done
L=""; for ((j = 0; j < i; j++)); do L="${L}[v${j}]"; done
ffmpeg -y -loglevel error "${ins[@]}" \
  -filter_complex "${f}${L}xstack=inputs=${i}:layout=${lay%|}:fill=white" "$out" && echo "ok: $out"
